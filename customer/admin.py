from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'email', 'company_name', 'phone', 'city', 'is_active', 'date_joined']
    list_filter = ['is_active', 'date_joined', 'country', 'state']
    search_fields = ['first_name', 'last_name', 'email', 'company_name', 'phone']
    readonly_fields = ['date_joined']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'first_name', 'last_name', 'email', 'company_name')
        }),
        ('Contact Details', {
            'fields': ('phone',)
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Additional Information', {
            'fields': ('is_active', 'notes', 'date_joined')
        }),
    )
