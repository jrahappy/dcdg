from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Organization, Customer, CustomerAddress, CustomerContact, CustomerNote, CustomerDocument

User = get_user_model()


class UserInline(admin.TabularInline):
    model = User
    extra = 0
    fields = ['email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser']
    readonly_fields = ['date_joined']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization_type', 'email', 'phone', 'city', 'member_count', 'is_active']
    list_filter = ['organization_type', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'tax_id', 'website']
    readonly_fields = ['created_at', 'updated_at', 'member_count']
    ordering = ['name']
    inlines = [UserInline]
    
    fieldsets = (
        ('Organization Information', {
            'fields': ('name', 'organization_type', 'tax_id', 'website')
        }),
        ('Contact Details', {
            'fields': ('email', 'phone')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Additional Information', {
            'fields': ('is_active', 'notes', 'created_at', 'updated_at')
        }),
    )
    
    def member_count(self, obj):
        return obj.member_count
    member_count.short_description = 'Members'


class CustomerContactInline(admin.TabularInline):
    model = CustomerContact
    extra = 1
    fields = ['first_name', 'last_name', 'email', 'phone', 'job_title', 'department', 'is_primary']


class CustomerNoteInline(admin.TabularInline):
    model = CustomerNote
    extra = 1
    fields = ['note', 'created_at']
    readonly_fields = ['created_at']


class CustomerDocumentInline(admin.TabularInline):
    model = CustomerDocument
    extra = 1
    fields = ['document', 'description', 'uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'email', 'company_name', 'company_category', 'phone', 'city', 'is_active', 'date_joined']
    list_filter = ['is_active', 'company_category', 'date_joined', 'country', 'state']
    search_fields = ['first_name', 'last_name', 'email', 'company_name', 'phone']
    readonly_fields = ['date_joined']
    ordering = ['-date_joined']
    inlines = [CustomerContactInline, CustomerNoteInline, CustomerDocumentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'company_category', 'company_name', 'first_name', 'last_name', 'email')
        }),
        ('Contact Details', {
            'fields': ('phone',)
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Additional Information', {
            'fields': ('is_active', 'internal_notes', 'date_joined')
        }),
    )


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ['customer', 'recipient_name', 'address_type', 'label', 'city', 'state', 'is_default', 'is_active']
    list_filter = ['address_type', 'is_default', 'is_active', 'created_at']
    search_fields = ['customer__email', 'customer__first_name', 'customer__last_name', 'recipient_name', 'address_line1', 'city', 'postal_code']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Customer & Type', {
            'fields': ('customer', 'address_type', 'label', 'is_default')
        }),
        ('Recipient Information', {
            'fields': ('recipient_name', 'company_name', 'phone')
        }),
        ('Address Details', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(CustomerContact)
class CustomerContactAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'customer', 'job_title', 'department', 'is_primary']
    list_filter = ['is_primary', 'department']
    search_fields = ['first_name', 'last_name', 'email', 'customer__company_name', 'customer__first_name', 'customer__last_name']
    ordering = ['-is_primary', 'last_name', 'first_name']


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ['customer', 'note_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['note', 'customer__company_name', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def note_preview(self, obj):
        return obj.note[:100] + '...' if len(obj.note) > 100 else obj.note
    note_preview.short_description = 'Note Preview'


@admin.register(CustomerDocument)
class CustomerDocumentAdmin(admin.ModelAdmin):
    list_display = ['customer', 'document', 'description', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['description', 'customer__company_name', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['uploaded_at']
    ordering = ['-uploaded_at']