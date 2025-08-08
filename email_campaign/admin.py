from django.contrib import admin
from .models import TargetGroup, EmailCampaign, EmailLog, PeriodicCampaign, PeriodicCampaignLog


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


@admin.register(PeriodicCampaign)
class PeriodicCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'target_group', 'frequency', 'status', 'next_run', 'last_run', 'total_sent']
    list_filter = ['status', 'frequency', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'last_run', 'total_sent']
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('name', 'description', 'target_group', 'email_template')
        }),
        ('Target Link Configuration', {
            'fields': ('target_link', 'target_link_parameter')
        }),
        ('Schedule', {
            'fields': ('frequency', 'start_date', 'end_date', 'next_run', 'last_run')
        }),
        ('Status', {
            'fields': ('status', 'total_sent')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(PeriodicCampaignLog)
class PeriodicCampaignLogAdmin(admin.ModelAdmin):
    list_display = ['periodic_campaign', 'started_at', 'status', 'recipients_count', 'sent_count', 'failed_count']
    list_filter = ['status', 'started_at']
    search_fields = ['periodic_campaign__name', 'error_message']
    readonly_fields = ['periodic_campaign', 'started_at', 'completed_at', 'status', 'recipients_count', 'sent_count', 'failed_count', 'error_message', 'email_campaign']
