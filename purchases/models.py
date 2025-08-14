from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from product.models import Product
from decimal import Decimal

User = get_user_model()


class Supplier(models.Model):
    """Supplier model for managing supplier information"""

    country_choices = [
        ("USA", "United States"),
        ("CAN", "Canada"),
        ("KOR", "Korea"),
    ]
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, choices=country_choices, default="USA")
    internal_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_suppliers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return self.name

    def get_full_address(self):
        """Return full address as a single string"""
        return f"{self.address_line1}, {self.address_line2}, {self.city}, {self.state}, {self.postal_code}, {self.country}"

    @property
    def full_address(self):
        """Property to access full address"""
        return self.get_full_address()


class SupplierContact(models.Model):
    """Contacts related to suppliers"""

    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="contacts"
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    position = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_supplier_contacts",
    )


class SupplierDocument(models.Model):
    """Documents related to suppliers"""

    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="documents"
    )
    document = models.FileField(upload_to="supplier_documents/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_supplier_documents",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Supplier Document"
        verbose_name_plural = "Supplier Documents"


class PurchaseOrder(models.Model):
    """Purchase orders for ordering products from suppliers"""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("confirmed", "Confirmed"),
        ("partially_received", "Partially Received"),
        ("received", "Fully Received"),
        ("cancelled", "Cancelled"),
    ]

    class ACCOUNTING_STATUS_CHOICES(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"

    # Accounting status
    accounting_status = models.CharField(
        max_length=20,
        choices=ACCOUNTING_STATUS_CHOICES.choices,
        default=ACCOUNTING_STATUS_CHOICES.DRAFT,
        help_text="Accounting status for invoices",
    )
    is_posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)

    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
        null=True,
        blank=True,
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Dates
    order_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Additional info
    reference_number = models.CharField(
        max_length=100, blank=True, help_text="Supplier's reference number"
    )
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # Tracking
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_purchase_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-order_date", "-created_at"]
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"

    def __str__(self):
        return f"PO {self.order_number} - {self.supplier.name}"

    def calculate_totals(self):
        """Recalculate order totals from line items"""
        items = self.items.all()
        self.subtotal = sum(item.line_total for item in items) or Decimal("0")

        # Calculate discount
        self.discount_amount = self.subtotal * (self.discount_percent / Decimal("100"))

        # Calculate tax
        taxable_amount = self.subtotal - self.discount_amount
        self.tax_amount = taxable_amount * (self.tax_rate / Decimal("100"))

        # Calculate total
        self.total_amount = taxable_amount + self.tax_amount + self.shipping_cost

        self.save()

    def update_receive_status(self):
        """Update order status based on received quantities"""
        items = self.items.all()
        if not items:
            return

        all_received = all(item.quantity_received >= item.quantity for item in items)
        any_received = any(item.quantity_received > 0 for item in items)

        if all_received:
            self.status = "received"
        elif any_received:
            self.status = "partially_received"

        self.save()


class PurchaseOrderItem(models.Model):
    """Line items for purchase orders"""

    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    # discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Receiving tracking(same to the inventory)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units"

    def save(self, *args, **kwargs):
        # Calculate line total
        # Ensure both values are Decimal to avoid type errors
        quantity = (
            Decimal(str(self.quantity)) if self.quantity is not None else Decimal("0")
        )
        unit_cost = (
            Decimal(str(self.unit_cost)) if self.unit_cost is not None else Decimal("0")
        )
        subtotal = quantity * unit_cost
        # discount = subtotal * (self.discount_percent / Decimal('100'))
        self.line_total = subtotal
        super().save(*args, **kwargs)

    @property
    def quantity_pending(self):
        """Calculate pending quantity to receive"""
        return max(self.quantity - self.quantity_received, Decimal("0"))

    @property
    def is_fully_received(self):
        """Check if all items have been received"""
        return self.quantity_received >= self.quantity


class SupplierPayment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"

    company = models.ForeignKey("customer.Organization", on_delete=models.CASCADE)
    supplier = models.ForeignKey(
        Supplier, null=True, blank=True, on_delete=models.SET_NULL
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder, null=True, blank=True, on_delete=models.SET_NULL
    )

    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    method = models.CharField(max_length=30, blank=True)  # e.g., Cash, Wire, Card
    bank_account_code = models.CharField(max_length=10, blank=True)  # "1010" 등
    is_advance = models.BooleanField(
        default=False
    )  # 선지급 여부(PO 단계 지급이면 True)
    advance_account_code = models.CharField(
        max_length=10, blank=True
    )  # 기본 "1310" 덮어쓰기용

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)

    def approve(self):
        from accounting.usecases import approve_and_post_outgoing_payment

        return approve_and_post_outgoing_payment(self)

    def __str__(self):
        return f"VendorPayment#{self.pk} {self.date} {self.amount}"
