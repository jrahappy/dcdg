from django.contrib import admin
from .models import EmailTemplate, EmailTemplateVariables


class EmailTemplateVariablesInline(admin.TabularInline):
    model = EmailTemplateVariables
    extra = 1
    fields = ['name', 'type', 'length', 'description', 'default_value', 'is_required', 'choices']


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'sender_email', 'content_type', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'content_type', 'created_at', 'updated_at']
    search_fields = ['title', 'subject', 'html_content', 'plain_content']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    inlines = [EmailTemplateVariablesInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subject', 'status')
        }),
        ('Sender Configuration', {
            'fields': ('sender_email', 'sender_name')
        }),
        ('Content', {
            'fields': ('content_type', 'html_content', 'plain_content')
        }),
        ('Tracking', {
            'fields': ('track_opens', 'track_clicks')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'available_variables'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailTemplateVariables)
class EmailTemplateVariablesAdmin(admin.ModelAdmin):
    list_display = ['template', 'name', 'type', 'length', 'is_required', 'description']
    list_filter = ['type', 'is_required', 'template']
    search_fields = ['name', 'description', 'template__title']