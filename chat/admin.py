from django.contrib import admin
from .models import ChatRoom, ChatMessage, ChatNotification


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['subject', 'customer', 'manager', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['subject', 'customer__email', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'manager')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['chat_room', 'sender', 'message_type', 'content_preview', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'created_at']
    search_fields = ['content', 'sender__email', 'sender__first_name', 'sender__last_name']
    readonly_fields = ['created_at', 'updated_at', 'read_at']
    ordering = ['-created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('chat_room', 'sender')


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'chat_room', 'message', 'is_seen', 'created_at']
    list_filter = ['is_seen', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'chat_room', 'message')