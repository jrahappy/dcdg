from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, SenderInformation, SenderEmail


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)


admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'created_at')
    search_fields = ('user__email', 'user__username', 'location')
    list_filter = ('created_at', 'updated_at')


class SenderEmailInline(admin.TabularInline):
    model = SenderEmail
    extra = 1
    fields = ('email', 'display_name', 'smtp_host', 'smtp_port', 'is_primary', 'is_verified')
    readonly_fields = ('is_verified', 'last_verified')


@admin.register(SenderInformation)
class SenderInformationAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'business_phone', 'created_at')
    search_fields = ('business_name', 'user__email', 'user__username')
    list_filter = ('created_at', 'updated_at')
    inlines = [SenderEmailInline]


@admin.register(SenderEmail)
class SenderEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'display_name', 'sender_info', 'smtp_host', 'is_primary', 'is_verified')
    search_fields = ('email', 'display_name', 'sender_info__business_name', 'smtp_host')
    list_filter = ('is_primary', 'is_verified', 'smtp_encryption', 'created_at')
    readonly_fields = ('last_verified', 'verification_error')
