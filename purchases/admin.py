from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderItem, Supplier, SupplierContact, SupplierDocument


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit_cost', 'line_total', 'quantity_received']
    readonly_fields = ['line_total']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'get_supplier_name', 'order_date', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'order_date', 'created_at']
    search_fields = ['order_number', 'supplier__name', 'supplier__email', 'reference_number']
    readonly_fields = ['subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'created_at', 'updated_at']
    inlines = [PurchaseOrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'supplier', 'status', 'order_date', 'expected_delivery_date', 'received_date', 'reference_number')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'shipping_cost', 
                      'discount_percent', 'discount_amount', 'total_amount')
        }),
        ('Additional Information', {
            'fields': ('notes', 'internal_notes', 'created_by', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_supplier_name(self, obj):
        return obj.supplier.name if obj.supplier else ''
    get_supplier_name.short_description = 'Supplier'
    get_supplier_name.admin_order_field = 'supplier__name'
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()
        
        # Recalculate totals after saving items
        if hasattr(form.instance, 'calculate_totals'):
            form.instance.calculate_totals()


# Register Supplier models
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'city', 'country', 'is_active']
    list_filter = ['is_active', 'country', 'created_at']
    search_fields = ['name', 'email', 'phone', 'contact_person']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'contact_person', 'email', 'phone', 'is_active')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Additional Information', {
            'fields': ('internal_notes', 'created_by', 'created_at', 'updated_at')
        }),
    )


class SupplierContactInline(admin.TabularInline):
    model = SupplierContact
    extra = 1
    fields = ['name', 'position', 'email', 'phone', 'notes']


class SupplierDocumentInline(admin.TabularInline):
    model = SupplierDocument
    extra = 1
    fields = ['document', 'description', 'uploaded_by', 'uploaded_at']
    readonly_fields = ['uploaded_by', 'uploaded_at']
