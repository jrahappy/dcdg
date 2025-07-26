from django.contrib import admin
from .models import TargetGroup, EmailCampaign, EmailLog


@admin.register(TargetGroup)
class TargetGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'customer_count', 'created_by', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['customers']
    
    def customer_count(self, obj):
        return obj.customer_count
    customer_count.short_description = 'Customers'


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'target_group', 'status', 'total_recipients', 'created_by', 'created_at']
    list_filter = ['status', 'created_at', 'sent_time']
    search_fields = ['name', 'subject', 'content']
    readonly_fields = ['created_at', 'updated_at', 'sent_time', 'total_recipients', 'sent_count', 'failed_count']
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('name', 'subject', 'content', 'from_email', 'target_group')
        }),
        ('Status', {
            'fields': ('status', 'scheduled_time', 'sent_time')
        }),
        ('Statistics', {
            'fields': ('total_recipients', 'sent_count', 'failed_count')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'customer', 'status', 'sent_at']
    list_filter = ['status', 'sent_at', 'campaign']
    search_fields = ['customer__email', 'customer__first_name', 'customer__last_name', 'campaign__name']
    readonly_fields = ['campaign', 'customer', 'status', 'sent_at', 'error_message']
