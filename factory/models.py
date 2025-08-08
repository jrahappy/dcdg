from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from sales.models import Invoice, InvoiceItem
from product.models import Product, Inventory
from customer.models import Customer
from purchases.models import Supplier

User = get_user_model()


class FactoryUser(models.Model):
    """
    Factory user profile linked to a supplier.
    Similar to Customer model but for factory/supplier side.
    """
    ROLE_CHOICES = [
        ('manager', 'Factory Manager'),
        ('supervisor', 'Supervisor'),
        ('worker', 'Factory Worker'),
        ('quality', 'Quality Control'),
        ('shipping', 'Shipping Staff'),
    ]
    
    # Link to Django User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='factory_profile')
    
    # Link to Supplier
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='factory_users')
    
    # Factory User Information
    employee_id = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker')
    department = models.CharField(max_length=100, blank=True)
    
    # Contact Information (additional to user)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    
    # Permissions
    can_approve_orders = models.BooleanField(default=False)
    can_manage_inventory = models.BooleanField(default=False)
    can_create_shipments = models.BooleanField(default=False)
    can_approve_supply_requests = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['supplier', 'user__first_name', 'user__last_name']
        verbose_name = 'Factory User'
        verbose_name_plural = 'Factory Users'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.supplier.name}"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def email(self):
        return self.user.email
    
    def get_assigned_work_orders(self):
        """Get work orders assigned to this factory user"""
        return WorkOrder.objects.filter(
            assigned_to=self.user,
            status__in=['pending', 'in_progress', 'ready']
        )
    
    def get_supplier_work_orders(self):
        """Get all work orders for this supplier"""
        # Get invoices that have items from this supplier's products
        from sales.models import Invoice
        invoice_ids = Invoice.objects.filter(
            items__product__supplier=self.supplier
        ).distinct().values_list('id', flat=True)
        
        return WorkOrder.objects.filter(
            invoice_id__in=invoice_ids
        ).order_by('-created_date')
    
    def can_access_work_order(self, work_order):
        """Check if this factory user can access a work order"""
        # Check if any items in the work order are from this supplier
        for item in work_order.invoice.items.all():
            if item.product and item.product.supplier == self.supplier:
                return True
        return False


# Signal to create FactoryUser when a user signs up with supplier flag
@receiver(post_save, sender=User)
def create_factory_user_profile(sender, instance, created, **kwargs):
    """
    Create a factory user profile when a user is created with is_factory_user flag
    or when explicitly needed.
    """
    if created and hasattr(instance, 'is_factory_user') and instance.is_factory_user:
        # This will be set during registration
        # The supplier will be set separately during the registration process
        pass  # FactoryUser creation will be handled in the registration view


class WorkOrder(models.Model):
    """
    Represents a work order for fulfilling invoice items.
    This tracks the production/preparation of items for shipping.
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready for Shipping'),
        ('shipped', 'Shipped'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]
    
    # Basic Information
    work_order_number = models.CharField(max_length=50, unique=True, db_index=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='work_orders')
    
    # Status and Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Dates
    created_date = models.DateTimeField(default=timezone.now)
    start_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    expected_completion = models.DateTimeField(null=True, blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='assigned_work_orders')
    department = models.CharField(max_length=100, blank=True, 
                                 help_text="Department responsible for fulfillment")
    
    # Notes
    internal_notes = models.TextField(blank=True)
    production_notes = models.TextField(blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='created_work_orders')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['invoice']),
        ]
    
    def __str__(self):
        return f"WO-{self.work_order_number} ({self.invoice.invoice_number})"
    
    def save(self, *args, **kwargs):
        if not self.work_order_number:
            # Generate work order number
            last_wo = WorkOrder.objects.order_by('-id').first()
            if last_wo and last_wo.work_order_number.startswith('WO'):
                try:
                    last_number = int(last_wo.work_order_number.split('-')[1])
                    self.work_order_number = f"WO-{last_number + 1:06d}"
                except (IndexError, ValueError):
                    self.work_order_number = "WO-000001"
            else:
                self.work_order_number = "WO-000001"
        super().save(*args, **kwargs)
    
    @property
    def progress_percentage(self):
        """Calculate fulfillment progress"""
        total_items = self.fulfillment_items.count()
        if total_items == 0:
            return 0
        completed_items = self.fulfillment_items.filter(status='fulfilled').count()
        return int((completed_items / total_items) * 100)
    
    @property
    def is_ready_to_ship(self):
        """Check if all items are ready for shipping"""
        return (self.fulfillment_items.exists() and 
                all(item.status == 'fulfilled' for item in self.fulfillment_items.all()))


class FulfillmentItem(models.Model):
    """
    Tracks the fulfillment status of individual invoice items.
    Links invoice items to inventory allocation.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('allocated', 'Inventory Allocated'),
        ('in_production', 'In Production'),
        ('quality_check', 'Quality Check'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]
    
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, 
                                  related_name='fulfillment_items')
    invoice_item = models.ForeignKey(InvoiceItem, on_delete=models.CASCADE, 
                                    related_name='fulfillment_items')
    
    # Quantity tracking
    quantity_ordered = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_fulfilled = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Inventory allocation
    allocated_inventory = models.ManyToManyField(Inventory, blank=True, 
                                                related_name='fulfillment_allocations')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Location tracking
    warehouse_location = models.CharField(max_length=100, blank=True)
    bin_location = models.CharField(max_length=50, blank=True)
    
    # Dates
    allocated_date = models.DateTimeField(null=True, blank=True)
    fulfilled_date = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    quality_check_notes = models.TextField(blank=True)
    
    # Tracking
    allocated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='allocated_items')
    fulfilled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='fulfilled_items')
    
    class Meta:
        ordering = ['work_order', 'invoice_item']
        unique_together = ['work_order', 'invoice_item']
    
    def __str__(self):
        return f"{self.invoice_item.product.name if self.invoice_item.product else 'Item'} - {self.status}"
    
    def allocate_inventory(self, inventory_items):
        """Allocate specific inventory items to this fulfillment"""
        for inventory in inventory_items:
            if inventory.status == 'available':
                self.allocated_inventory.add(inventory)
                inventory.status = 'allocated'
                inventory.save()
                self.quantity_allocated += 1
        
        if self.quantity_allocated > 0:
            self.status = 'allocated'
            self.allocated_date = timezone.now()
        self.save()
    
    def mark_fulfilled(self, user=None):
        """Mark item as fulfilled"""
        self.status = 'fulfilled'
        self.quantity_fulfilled = self.quantity_ordered
        self.fulfilled_date = timezone.now()
        if user:
            self.fulfilled_by = user
        
        # Update allocated inventory status
        for inventory in self.allocated_inventory.all():
            inventory.status = 'sold'
            inventory.save()
        
        self.save()


class Shipment(models.Model):
    """
    Manages shipping of fulfilled orders to customers.
    """
    CARRIER_CHOICES = [
        ('ups', 'UPS'),
        ('fedex', 'FedEx'),
        ('usps', 'USPS'),
        ('dhl', 'DHL'),
        ('internal', 'Internal Delivery'),
        ('pickup', 'Customer Pickup'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('preparing', 'Preparing'),
        ('ready', 'Ready to Ship'),
        ('picked_up', 'Picked Up by Carrier'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Information
    shipment_number = models.CharField(max_length=50, unique=True, db_index=True)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, 
                                  related_name='shipments')
    
    # Shipping Details
    carrier = models.CharField(max_length=20, choices=CARRIER_CHOICES)
    tracking_number = models.CharField(max_length=100, blank=True, db_index=True)
    service_type = models.CharField(max_length=100, blank=True, 
                                   help_text="e.g., Ground, 2-Day, Overnight")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing')
    
    # Addresses (copied from invoice at time of shipping)
    ship_to_name = models.CharField(max_length=200)
    ship_to_company = models.CharField(max_length=200, blank=True)
    ship_to_address_line1 = models.CharField(max_length=255)
    ship_to_address_line2 = models.CharField(max_length=255, blank=True)
    ship_to_city = models.CharField(max_length=100)
    ship_to_state = models.CharField(max_length=50)
    ship_to_postal_code = models.CharField(max_length=20)
    ship_to_country = models.CharField(max_length=2, default='US')
    ship_to_phone = models.CharField(max_length=20, blank=True)
    ship_to_email = models.EmailField(blank=True)
    
    # Package Information
    number_of_packages = models.IntegerField(default=1)
    total_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text="Total weight in pounds")
    package_dimensions = models.CharField(max_length=100, blank=True, 
                                        help_text="L x W x H in inches")
    
    # Costs
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    insurance_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Dates
    created_date = models.DateTimeField(default=timezone.now)
    ship_date = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    
    # Documents
    packing_list_generated = models.BooleanField(default=False)
    shipping_label_generated = models.BooleanField(default=False)
    customs_forms_required = models.BooleanField(default=False)
    customs_forms_completed = models.BooleanField(default=False)
    
    # Notes
    special_instructions = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    delivery_signature = models.CharField(max_length=200, blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  related_name='created_shipments')
    shipped_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='processed_shipments')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['work_order']),
        ]
    
    def __str__(self):
        return f"SHIP-{self.shipment_number} ({self.tracking_number or 'No tracking'})"
    
    def save(self, *args, **kwargs):
        if not self.shipment_number:
            # Generate shipment number
            last_ship = Shipment.objects.order_by('-id').first()
            if last_ship and last_ship.shipment_number.startswith('SHIP'):
                try:
                    last_number = int(last_ship.shipment_number.split('-')[1])
                    self.shipment_number = f"SHIP-{last_number + 1:06d}"
                except (IndexError, ValueError):
                    self.shipment_number = "SHIP-000001"
            else:
                self.shipment_number = "SHIP-000001"
        
        # Copy shipping address from invoice if not set
        if not self.ship_to_name and self.work_order:
            invoice = self.work_order.invoice
            if invoice.shipping_same_as_billing:
                self.ship_to_name = invoice.customer.get_full_name() if invoice.customer else f"{invoice.first_name} {invoice.last_name}"
                self.ship_to_company = invoice.customer.company_name if invoice.customer else ""
                self.ship_to_address_line1 = invoice.billing_address_line1
                self.ship_to_address_line2 = invoice.billing_address_line2
                self.ship_to_city = invoice.billing_city
                self.ship_to_state = invoice.billing_state
                self.ship_to_postal_code = invoice.billing_postal_code
                self.ship_to_country = invoice.billing_country
            else:
                self.ship_to_name = invoice.customer.get_full_name() if invoice.customer else f"{invoice.first_name} {invoice.last_name}"
                self.ship_to_company = invoice.customer.company_name if invoice.customer else ""
                self.ship_to_address_line1 = invoice.shipping_address_line1
                self.ship_to_address_line2 = invoice.shipping_address_line2
                self.ship_to_city = invoice.shipping_city
                self.ship_to_state = invoice.shipping_state
                self.ship_to_postal_code = invoice.shipping_postal_code
                self.ship_to_country = invoice.shipping_country
            
            self.ship_to_phone = invoice.customer.phone if invoice.customer else invoice.phone
            self.ship_to_email = invoice.customer.email if invoice.customer else invoice.email
        
        super().save(*args, **kwargs)
    
    def mark_shipped(self, tracking_number=None, user=None):
        """Mark shipment as shipped"""
        self.status = 'in_transit'
        self.ship_date = timezone.now()
        if tracking_number:
            self.tracking_number = tracking_number
        if user:
            self.shipped_by = user
        self.save()
        
        # Update work order status
        self.work_order.status = 'shipped'
        self.work_order.save()
    
    def mark_delivered(self, signature=None):
        """Mark shipment as delivered"""
        self.status = 'delivered'
        self.actual_delivery = timezone.now()
        if signature:
            self.delivery_signature = signature
        self.save()
        
        # Update work order status
        self.work_order.status = 'completed'
        self.work_order.completion_date = timezone.now()
        self.work_order.save()


class SupplyRequest(models.Model):
    """
    Tracks requests for supplies/inventory needed to fulfill orders.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # Basic Information
    request_number = models.CharField(max_length=50, unique=True)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, 
                                  related_name='supply_requests', null=True, blank=True)
    
    # Product Information
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_requested = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_approved = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status and Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='normal')
    
    # Dates
    requested_date = models.DateTimeField(default=timezone.now)
    needed_by = models.DateField()
    approved_date = models.DateTimeField(null=True, blank=True)
    ordered_date = models.DateTimeField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)
    
    # Approval
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='supply_requests_created')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='supply_requests_approved')
    
    # Supplier Information
    supplier_name = models.CharField(max_length=200, blank=True)
    purchase_order_number = models.CharField(max_length=50, blank=True)
    
    # Notes
    reason = models.TextField(help_text="Reason for supply request")
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-requested_date']
        indexes = [
            models.Index(fields=['status', 'urgency']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"SR-{self.request_number} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            # Generate request number
            last_sr = SupplyRequest.objects.order_by('-id').first()
            if last_sr and last_sr.request_number.startswith('SR'):
                try:
                    last_number = int(last_sr.request_number.split('-')[1])
                    self.request_number = f"SR-{last_number + 1:06d}"
                except (IndexError, ValueError):
                    self.request_number = "SR-000001"
            else:
                self.request_number = "SR-000001"
        super().save(*args, **kwargs)
    
    def approve(self, user, approved_quantity=None):
        """Approve the supply request"""
        self.status = 'approved'
        self.approved_date = timezone.now()
        self.approved_by = user
        if approved_quantity:
            self.quantity_approved = approved_quantity
        else:
            self.quantity_approved = self.quantity_requested
        self.save()
