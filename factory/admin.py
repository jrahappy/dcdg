from django.contrib import admin
from django.utils.html import format_html
from .models import WorkOrder, FulfillmentItem, Shipment, SupplyRequest, FactoryUser


@admin.register(FactoryUser)
class FactoryUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'supplier', 'role', 'department', 'is_active', 'date_joined']
    list_filter = ['supplier', 'role', 'is_active', 'can_approve_orders', 
                   'can_manage_inventory', 'can_create_shipments']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 
                    'supplier__name', 'employee_id']
    readonly_fields = ['date_joined', 'last_activity']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'supplier', 'employee_id')
        }),
        ('Role & Department', {
            'fields': ('role', 'department')
        }),
        ('Contact Information', {
            'fields': ('phone', 'mobile')
        }),
        ('Permissions', {
            'fields': ('can_approve_orders', 'can_manage_inventory', 
                      'can_create_shipments', 'can_approve_supply_requests')
        }),
        ('Status', {
            'fields': ('is_active', 'date_joined', 'last_activity')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'supplier')


class FulfillmentItemInline(admin.TabularInline):
    model = FulfillmentItem
    extra = 0
    fields = ['invoice_item', 'quantity_ordered', 'quantity_allocated', 
              'quantity_fulfilled', 'status', 'warehouse_location']
    readonly_fields = ['invoice_item', 'quantity_ordered']


class ShipmentInline(admin.StackedInline):
    model = Shipment
    extra = 0
    fields = ['shipment_number', 'carrier', 'tracking_number', 'status', 'ship_date']
    readonly_fields = ['shipment_number']


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ['work_order_number', 'invoice_link', 'customer_name', 
                   'status', 'priority', 'progress_bar', 'created_date']
    list_filter = ['status', 'priority', 'created_date', 'department']
    search_fields = ['work_order_number', 'invoice__invoice_number', 
                    'invoice__customer__first_name', 'invoice__customer__last_name']
    readonly_fields = ['work_order_number', 'progress_percentage', 'is_ready_to_ship', 
                      'created_date', 'updated_at']
    inlines = [FulfillmentItemInline, ShipmentInline]
    
    fieldsets = (
        ('Work Order Information', {
            'fields': ('work_order_number', 'invoice', 'status', 'priority')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'department')
        }),
        ('Dates', {
            'fields': ('created_date', 'start_date', 'expected_completion', 
                      'completion_date', 'updated_at')
        }),
        ('Progress', {
            'fields': ('progress_percentage', 'is_ready_to_ship')
        }),
        ('Notes', {
            'fields': ('internal_notes', 'production_notes')
        }),
    )
    
    def invoice_link(self, obj):
        if obj.invoice:
            url = f"/admin/sales/invoice/{obj.invoice.pk}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.invoice.invoice_number)
        return '-'
    invoice_link.short_description = 'Invoice'
    
    def customer_name(self, obj):
        if obj.invoice and obj.invoice.customer:
            return obj.invoice.customer.get_full_name()
        elif obj.invoice:
            return f"{obj.invoice.first_name} {obj.invoice.last_name}"
        return '-'
    customer_name.short_description = 'Customer'
    
    def progress_bar(self, obj):
        percentage = obj.progress_percentage
        color = 'green' if percentage == 100 else 'orange' if percentage > 50 else 'red'
        return format_html(
            '<div style="width:100px;height:20px;border:1px solid #ccc;background:#f0f0f0;">'
            '<div style="width:{}%;height:100%;background:{};">&nbsp;</div>'
            '</div><small>{}%</small>',
            percentage, color, percentage
        )
    progress_bar.short_description = 'Progress'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New work order
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_in_progress', 'mark_ready_to_ship']
    
    def mark_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
    mark_in_progress.short_description = "Mark selected as In Progress"
    
    def mark_ready_to_ship(self, request, queryset):
        queryset.update(status='ready')
    mark_ready_to_ship.short_description = "Mark selected as Ready to Ship"


@admin.register(FulfillmentItem)
class FulfillmentItemAdmin(admin.ModelAdmin):
    list_display = ['work_order', 'product_name', 'quantity_ordered', 
                   'quantity_allocated', 'quantity_fulfilled', 'status', 
                   'warehouse_location']
    list_filter = ['status', 'allocated_date', 'fulfilled_date']
    search_fields = ['work_order__work_order_number', 
                    'invoice_item__product__name']
    readonly_fields = ['allocated_date', 'fulfilled_date']
    filter_horizontal = ['allocated_inventory']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('work_order', 'invoice_item')
        }),
        ('Quantities', {
            'fields': ('quantity_ordered', 'quantity_allocated', 'quantity_fulfilled')
        }),
        ('Status & Location', {
            'fields': ('status', 'warehouse_location', 'bin_location')
        }),
        ('Inventory Allocation', {
            'fields': ('allocated_inventory',)
        }),
        ('Dates & Tracking', {
            'fields': ('allocated_date', 'allocated_by', 'fulfilled_date', 'fulfilled_by')
        }),
        ('Notes', {
            'fields': ('notes', 'quality_check_notes')
        }),
    )
    
    def product_name(self, obj):
        if obj.invoice_item and obj.invoice_item.product:
            return obj.invoice_item.product.name
        return 'Custom Item'
    product_name.short_description = 'Product'
    
    actions = ['mark_allocated', 'mark_fulfilled']
    
    def mark_allocated(self, request, queryset):
        for item in queryset:
            item.status = 'allocated'
            item.allocated_by = request.user
            item.save()
    mark_allocated.short_description = "Mark selected as Allocated"
    
    def mark_fulfilled(self, request, queryset):
        for item in queryset:
            item.mark_fulfilled(user=request.user)
    mark_fulfilled.short_description = "Mark selected as Fulfilled"


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ['shipment_number', 'work_order', 'carrier', 'tracking_number', 
                   'status', 'ship_date', 'estimated_delivery']
    list_filter = ['status', 'carrier', 'ship_date', 'created_date']
    search_fields = ['shipment_number', 'tracking_number', 
                    'work_order__work_order_number']
    readonly_fields = ['shipment_number', 'created_date', 'updated_at']
    date_hierarchy = 'ship_date'
    
    fieldsets = (
        ('Shipment Information', {
            'fields': ('shipment_number', 'work_order', 'carrier', 
                      'tracking_number', 'service_type', 'status')
        }),
        ('Shipping Address', {
            'fields': ('ship_to_name', 'ship_to_company', 'ship_to_address_line1', 
                      'ship_to_address_line2', 'ship_to_city', 'ship_to_state', 
                      'ship_to_postal_code', 'ship_to_country', 'ship_to_phone', 
                      'ship_to_email')
        }),
        ('Package Details', {
            'fields': ('number_of_packages', 'total_weight', 'package_dimensions')
        }),
        ('Costs', {
            'fields': ('shipping_cost', 'insurance_cost')
        }),
        ('Dates', {
            'fields': ('created_date', 'ship_date', 'estimated_delivery', 
                      'actual_delivery', 'updated_at')
        }),
        ('Documents', {
            'fields': ('packing_list_generated', 'shipping_label_generated', 
                      'customs_forms_required', 'customs_forms_completed')
        }),
        ('Notes & Tracking', {
            'fields': ('special_instructions', 'internal_notes', 
                      'delivery_signature', 'created_by', 'shipped_by')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New shipment
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_shipped', 'mark_delivered', 'generate_shipping_label']
    
    def mark_shipped(self, request, queryset):
        for shipment in queryset:
            shipment.mark_shipped(user=request.user)
    mark_shipped.short_description = "Mark selected as Shipped"
    
    def mark_delivered(self, request, queryset):
        for shipment in queryset:
            shipment.mark_delivered()
    mark_delivered.short_description = "Mark selected as Delivered"
    
    def generate_shipping_label(self, request, queryset):
        queryset.update(shipping_label_generated=True)
    generate_shipping_label.short_description = "Generate Shipping Labels"


@admin.register(SupplyRequest)
class SupplyRequestAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'product', 'quantity_requested', 
                   'quantity_approved', 'status', 'urgency', 'needed_by', 
                   'requested_date']
    list_filter = ['status', 'urgency', 'requested_date', 'needed_by']
    search_fields = ['request_number', 'product__name', 'supplier_name']
    readonly_fields = ['request_number', 'requested_date', 'approved_date', 
                      'ordered_date', 'received_date']
    date_hierarchy = 'needed_by'
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_number', 'work_order', 'product', 'reason')
        }),
        ('Quantities', {
            'fields': ('quantity_requested', 'quantity_approved', 'quantity_received')
        }),
        ('Status & Priority', {
            'fields': ('status', 'urgency', 'needed_by')
        }),
        ('Dates', {
            'fields': ('requested_date', 'approved_date', 'ordered_date', 
                      'received_date')
        }),
        ('Approval & Supplier', {
            'fields': ('requested_by', 'approved_by', 'supplier_name', 
                      'purchase_order_number')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New request
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['approve_requests', 'mark_ordered', 'mark_received']
    
    def approve_requests(self, request, queryset):
        for req in queryset:
            req.approve(user=request.user)
    approve_requests.short_description = "Approve selected requests"
    
    def mark_ordered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='ordered', ordered_date=timezone.now())
    mark_ordered.short_description = "Mark selected as Ordered"
    
    def mark_received(self, request, queryset):
        from django.utils import timezone
        for req in queryset:
            req.status = 'received'
            req.received_date = timezone.now()
            req.quantity_received = req.quantity_approved or req.quantity_requested
            req.save()
    mark_received.short_description = "Mark selected as Received"
