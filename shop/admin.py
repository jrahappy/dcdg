from django.contrib import admin
from .models import Cart, CartItem, ShippingRate, PromoCode


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'user', 'total_items', 'subtotal', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['session_key', 'user__email']
    readonly_fields = ['total_items', 'subtotal']
    inlines = [CartItemInline]


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_rate', 'per_item_rate', 'estimated_days', 'is_active', 'sort_order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'sort_order']


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'description', 'discount_type', 'discount_value', 'usage_limit', 'used_count', 'is_active', 'valid_until']
    list_filter = ['is_active', 'discount_type', 'valid_from', 'valid_until']
    search_fields = ['code', 'description']
    readonly_fields = ['used_count']