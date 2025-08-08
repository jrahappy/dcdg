import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class Cart(models.Model):
    """Shopping cart for anonymous users"""
    session_key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Optional: link to user if they log in
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Cart {self.session_key[:8]}..."
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        from decimal import Decimal
        return sum(item.line_total for item in self.items.all()) or Decimal('0')
    
    def clear(self):
        """Empty the cart"""
        self.items.all().delete()


class CartItem(models.Model):
    """Items in shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    # Store price at time of adding to cart
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Store selected options as JSON
    selected_options = models.JSONField(default=dict, blank=True)
    # Format: {"Color": "Red", "Size": "Large"}
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        # Remove unique_together to allow same product with different options
    
    def __str__(self):
        options_str = ""
        if self.selected_options:
            options_str = " - " + ", ".join([f"{k}: {v}" for k, v in self.selected_options.items()])
        return f"{self.product.name}{options_str} x {self.quantity}"
    
    def get_options_display(self):
        """Get formatted display of selected options"""
        if not self.selected_options:
            return ""
        return ", ".join([f"{k}: {v}" for k, v in self.selected_options.items()])
    
    @property
    def line_total(self):
        return self.unit_price * self.quantity


class ShippingRate(models.Model):
    """Shipping rates configuration"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    per_item_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_days = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'base_rate']
    
    def __str__(self):
        return self.name
    
    def calculate_cost(self, subtotal, item_count):
        """Calculate shipping cost based on order details"""
        if self.min_order_amount and subtotal < self.min_order_amount:
            return None  # Not eligible
        if self.max_order_amount and subtotal > self.max_order_amount:
            return None  # Not eligible
        
        return self.base_rate + (self.per_item_rate * item_count)


class PromoCode(models.Model):
    """Promotional codes for discounts"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Usage limits
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    
    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    
    # Conditions
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.code
    
    def is_valid(self):
        """Check if promo code is currently valid"""
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if self.valid_from > now:
            return False
        
        if self.valid_until and self.valid_until < now:
            return False
        
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        
        return True
    
    def calculate_discount(self, subtotal):
        """Calculate discount amount based on subtotal"""
        if not self.is_valid():
            return Decimal('0')
        
        if self.min_order_amount and subtotal < self.min_order_amount:
            return Decimal('0')
        
        if self.discount_type == 'percentage':
            return subtotal * (self.discount_value / 100)
        elif self.discount_type == 'fixed':
            return min(self.discount_value, subtotal)
        
        return Decimal('0')