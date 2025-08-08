from django.contrib import admin
from django.utils.html import format_html
from .models import Product, ProductDoc, ProductImage, Inventory, Category, ProductOptionName, ProductOptionItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'parent',
        'slug',
        'is_active',
        'order',
        'product_count',
        'created_at'
    ]
    list_filter = [
        'is_active',
        'parent',
        'created_at'
    ]
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        ('Display Options', {
            'fields': ('icon', 'order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def product_count(self, obj):
        return obj.get_product_count()
    product_count.short_description = 'Product Count'
    
    def get_queryset(self, request):
        """Override to add custom annotations if needed"""
        qs = super().get_queryset(request)
        return qs.select_related('parent')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'caption', 'is_primary', 'order']


class ProductDocInline(admin.TabularInline):
    model = ProductDoc
    extra = 1
    fields = ['title', 'doc_type', 'file', 'is_public']
    readonly_fields = ['file_size', 'download_count']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'sku', 
        'category', 
        'display_price_formatted', 
        'stock_status',
        'status',
        'is_featured',
        'created_at'
    ]
    list_filter = [
        'status', 
        'category', 
        'is_featured', 
        'brand',
        'created_at'
    ]
    search_fields = [
        'name', 
        'sku', 
        'short_description', 
        'brand', 
        'manufacturer',
        'tags'
    ]
    ordering = ['-created_at']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'views_count',
        'display_price',
        'margin_percentage'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'slug',
                'sku',
                'category',
                'brand',
                'manufacturer'
            )
        }),
        ('Description', {
            'fields': (
                'short_description',
                'long_description',
                'features',
                'specifications',
                'tags'
            )
        }),
        ('Pricing', {
            'fields': (
                'price',
                'cost',
                'discount_percentage',
                'display_price',
                'margin_percentage'
            )
        }),
        ('Inventory', {
            'fields': (
                'quantity_in_stock',
                'minimum_stock_level',
                'weight',
                'dimensions',
                'is_serial_number_managed'
            )
        }),
        ('Images', {
            'fields': (
                'main_image',
                'thumbnail_image'
            )
        }),
        ('Status & Metadata', {
            'fields': (
                'status',
                'is_featured',
                'created_by',
                'created_at',
                'updated_at',
                'views_count'
            )
        })
    )
    
    inlines = [ProductImageInline, ProductDocInline]
    
    def display_price_formatted(self, obj):
        if obj.discount_percentage > 0:
            return format_html(
                '<span style="text-decoration: line-through;">${}</span> <span style="color: green;">${}</span>',
                obj.price,
                obj.display_price
            )
        return f"${obj.price}"
    display_price_formatted.short_description = "Price"
    
    def stock_status(self, obj):
        if obj.quantity_in_stock == 0:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.is_low_stock:
            return format_html(
                '<span style="color: orange;">Low Stock ({})</span>',
                obj.quantity_in_stock
            )
        else:
            return format_html(
                '<span style="color: green;">In Stock ({})</span>',
                obj.quantity_in_stock
            )
    stock_status.short_description = "Stock Status"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductDoc)
class ProductDocAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'product',
        'doc_type',
        'file_extension',
        'file_size_mb',
        'is_public',
        'download_count',
        'uploaded_at'
    ]
    list_filter = [
        'doc_type',
        'is_public',
        'uploaded_at'
    ]
    search_fields = [
        'title',
        'description',
        'product__name'
    ]
    readonly_fields = [
        'file_size',
        'file_size_mb',
        'file_extension',
        'download_count',
        'uploaded_by',
        'uploaded_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': (
                'product',
                'title',
                'doc_type',
                'description'
            )
        }),
        ('File Details', {
            'fields': (
                'file',
                'file_size_mb',
                'file_extension',
                'is_public'
            )
        }),
        ('Statistics', {
            'fields': (
                'download_count',
                'uploaded_by',
                'uploaded_at',
                'updated_at'
            )
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating a new object
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = [
        'product',
        'caption',
        'is_primary',
        'order',
        'uploaded_at'
    ]
    list_filter = [
        'is_primary',
        'uploaded_at'
    ]
    search_fields = [
        'product__name',
        'caption'
    ]
    ordering = ['product', 'order']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = [
        'serial_number',
        'product',
        'status',
        'warranty_status_display',
        'customer',
        'current_location',
        'purchase_date',
        'warranty_end_date'
    ]
    list_filter = [
        'status',
        'warranty_status',
        'condition',
        'product__category',
        'purchase_date',
        'warranty_end_date'
    ]
    search_fields = [
        'serial_number',
        'batch_number',
        'barcode',
        'product__name',
        'product__sku',
        'customer__first_name',
        'customer__last_name',
        'customer__email',
        'supplier',
        'current_location'
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'is_under_warranty',
        'warranty_days_remaining',
        'age_in_days',
        'profit_margin'
    ]
    autocomplete_fields = ['product', 'customer']
    date_hierarchy = 'purchase_date'
    
    fieldsets = (
        ('Product Information', {
            'fields': (
                'product',
                'serial_number',
                'batch_number',
                'barcode',
                'qr_code'
            )
        }),
        ('Status & Condition', {
            'fields': (
                'status',
                'condition',
                'current_location'
            )
        }),
        ('Purchase Information', {
            'fields': (
                'purchase_date',
                'purchase_price',
                'supplier',
                'purchase_order_number',
                'age_in_days'
            )
        }),
        ('Warranty Information', {
            'fields': (
                'warranty_start_date',
                'warranty_end_date',
                'warranty_status',
                'warranty_provider',
                'warranty_terms',
                'extended_warranty_end_date',
                'is_under_warranty',
                'warranty_days_remaining'
            ),
            'classes': ('collapse',)
        }),
        ('Sales Information', {
            'fields': (
                'customer',
                'sale_date',
                'sale_price',
                'profit_margin'
            ),
            'classes': ('collapse',)
        }),
        ('Assignment', {
            'fields': (
                'assigned_to',
                'assigned_date'
            ),
            'classes': ('collapse',)
        }),
        ('Service & Maintenance', {
            'fields': (
                'last_service_date',
                'next_service_date',
                'service_history'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': (
                'notes',
                'created_by',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def warranty_status_display(self, obj):
        if obj.warranty_status == 'active':
            days = obj.warranty_days_remaining
            if days <= 30:
                return format_html(
                    '<span style="color: orange;">Active ({} days left)</span>',
                    days
                )
            return format_html(
                '<span style="color: green;">Active ({} days left)</span>',
                days
            )
        elif obj.warranty_status == 'expired':
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.warranty_status == 'extended':
            return format_html('<span style="color: blue;">Extended</span>')
        elif obj.warranty_status == 'void':
            return format_html('<span style="color: gray;">Void</span>')
        return obj.get_warranty_status_display()
    warranty_status_display.short_description = "Warranty Status"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating a new object
            obj.created_by = request.user
        # Auto-update warranty status
        obj.update_warranty_status()
        super().save_model(request, obj, form, change)
    
    actions = ['update_warranty_status_action', 'mark_as_sold', 'mark_as_defective']
    
    def update_warranty_status_action(self, request, queryset):
        for item in queryset:
            item.update_warranty_status()
        self.message_user(request, f"Updated warranty status for {queryset.count()} items.")
    update_warranty_status_action.short_description = "Update warranty status"
    
    def mark_as_sold(self, request, queryset):
        count = queryset.filter(status='available').update(status='sold')
        self.message_user(request, f"Marked {count} items as sold.")
    mark_as_sold.short_description = "Mark selected items as sold"
    
    def mark_as_defective(self, request, queryset):
        count = queryset.update(status='defective')
        self.message_user(request, f"Marked {count} items as defective.")
    mark_as_defective.short_description = "Mark selected items as defective"


class ProductOptionItemInline(admin.TabularInline):
    """Inline admin for product option items"""
    model = ProductOptionItem
    extra = 1
    fields = ['value', 'ordering', 'is_active']
    ordering = ['ordering', 'value']


@admin.register(ProductOptionName)
class ProductOptionNameAdmin(admin.ModelAdmin):
    """Admin for product option names (e.g., Color, Size)"""
    list_display = [
        'name',
        'description',
        'item_count',
        'is_active',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'is_active',
        'created_at'
    ]
    search_fields = [
        'name',
        'description'
    ]
    ordering = ['name']
    inlines = [ProductOptionItemInline]
    
    fieldsets = (
        ('Option Information', {
            'fields': (
                'name',
                'description',
                'is_active'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def item_count(self, obj):
        """Count of option items for this option name"""
        return obj.items.count()
    item_count.short_description = "Items"


@admin.register(ProductOptionItem)
class ProductOptionItemAdmin(admin.ModelAdmin):
    """Admin for product option items (e.g., Red, Blue, Large)"""
    list_display = [
        'value',
        'option_name',
        'ordering',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'option_name',
        'is_active',
        'created_at'
    ]
    search_fields = [
        'value',
        'option_name__name'
    ]
    ordering = ['option_name', 'ordering', 'value']
    
    fieldsets = (
        ('Option Item Information', {
            'fields': (
                'option_name',
                'value',
                'ordering',
                'is_active'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
            ),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['created_at']