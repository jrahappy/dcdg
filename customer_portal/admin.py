from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username', 'user__email']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'read_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'message', 'notification_type', 'priority')
        }),
        ('Link', {
            'fields': ('link',),
            'description': 'Optional link for the notification (e.g., to an order or product)'
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'created_at')
        }),
    )
    
    def mark_as_read(self, request, queryset):
        """Admin action to mark notifications as read"""
        count = 0
        for notification in queryset.filter(is_read=False):
            notification.mark_as_read()
            count += 1
        self.message_user(request, f'{count} notifications marked as read.')
    
    def mark_as_unread(self, request, queryset):
        """Admin action to mark notifications as unread"""
        count = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{count} notifications marked as unread.')
    
    actions = ['mark_as_read', 'mark_as_unread']
