from django.contrib import admin
from .models import (
    Quote, QuoteItem, Order, OrderItem, 
    Invoice, InvoiceItem, Payment, 
    CreditNote, CreditNoteItem
)


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent', 'line_total']
    readonly_fields = ['line_total']


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_number', 'customer', 'status', 'quote_date', 'valid_until', 'total_amount']
    list_filter = ['status', 'quote_date', 'valid_until']
    search_fields = ['quote_number', 'customer__first_name', 'customer__last_name', 'customer__email']
    date_hierarchy = 'quote_date'
    inlines = [QuoteItemInline]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('quote_number', 'customer', 'status', 'quote_date', 'valid_until')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'discount_percent', 
                      'discount_amount', 'total_amount')
        }),
        ('Additional Information', {
            'fields': ('terms_and_conditions', 'notes')
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent', 
              'line_total', 'quantity_shipped', 'quantity_delivered']
    readonly_fields = ['line_total']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'status', 'payment_status', 
                   'order_date', 'total_amount', 'balance_due']
    list_filter = ['status', 'payment_status', 'order_date']
    search_fields = ['order_number', 'customer__first_name', 'customer__last_name', 
                    'customer__email', 'purchase_order_number']
    date_hierarchy = 'order_date'
    inlines = [OrderItemInline]
    readonly_fields = ['created_at', 'updated_at', 'balance_due']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('order_number', 'customer', 'quote', 'status', 'payment_status', 
                      'order_date', 'delivery_date', 'shipped_date')
        }),
        ('Shipping Address', {
            'fields': ('shipping_address_line1', 'shipping_address_line2', 'shipping_city', 
                      'shipping_state', 'shipping_postal_code', 'shipping_country')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'shipping_cost', 'tax_rate', 'tax_amount', 
                      'discount_percent', 'discount_amount', 'total_amount', 
                      'paid_amount', 'balance_due')
        }),
        ('Additional Information', {
            'fields': ('purchase_order_number', 'notes', 'internal_notes')
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent', 'line_total']
    readonly_fields = ['line_total']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'status', 'invoice_date', 
                   'due_date', 'total_amount', 'balance_due']
    list_filter = ['status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'customer__first_name', 'customer__last_name', 
                    'customer__email']
    date_hierarchy = 'invoice_date'
    inlines = [InvoiceItemInline]
    readonly_fields = ['created_at', 'updated_at', 'balance_due', 'sent_date', 'viewed_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('invoice_number', 'customer', 'order', 'status', 
                      'invoice_date', 'due_date')
        }),
        ('Billing Address', {
            'fields': ('billing_address_line1', 'billing_address_line2', 'billing_city', 
                      'billing_state', 'billing_postal_code', 'billing_country')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'discount_percent', 
                      'discount_amount', 'total_amount', 'paid_amount', 'balance_due')
        }),
        ('Payment Terms', {
            'fields': ('payment_terms', 'late_fee_percent')
        }),
        ('Additional Information', {
            'fields': ('notes', 'internal_notes')
        }),
        ('Email Tracking', {
            'fields': ('sent_date', 'viewed_date')
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'customer', 'amount', 'payment_date', 
                   'payment_method', 'status']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['payment_number', 'customer__first_name', 'customer__last_name', 
                    'customer__email', 'reference_number']
    date_hierarchy = 'payment_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('payment_number', 'customer', 'invoice', 'order')
        }),
        ('Payment Details', {
            'fields': ('amount', 'payment_date', 'payment_method', 'status')
        }),
        ('Reference Information', {
            'fields': ('reference_number', 'bank_name')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Tracking', {
            'fields': ('processed_by', 'created_at', 'updated_at')
        }),
    )


class CreditNoteItemInline(admin.TabularInline):
    model = CreditNoteItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit_price', 'line_total']
    readonly_fields = ['line_total']


@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = ['credit_note_number', 'customer', 'status', 'issue_date', 
                   'total_amount', 'balance']
    list_filter = ['status', 'issue_date']
    search_fields = ['credit_note_number', 'customer__first_name', 'customer__last_name', 
                    'customer__email', 'reason']
    date_hierarchy = 'issue_date'
    inlines = [CreditNoteItemInline]
    readonly_fields = ['created_at', 'updated_at', 'balance']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('credit_note_number', 'customer', 'invoice', 'order', 
                      'status', 'issue_date')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'total_amount', 'applied_amount', 'balance')
        }),
        ('Details', {
            'fields': ('reason', 'notes')
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )