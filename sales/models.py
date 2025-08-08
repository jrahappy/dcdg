from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from customer.models import Customer
from product.models import Product


class Quote(models.Model):
    """Sales quote/estimate for customers"""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
        ("converted", "Converted to Order"),
    ]

    quote_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="quotes"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Dates
    quote_date = models.DateField()
    valid_until = models.DateField()

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Additional info
    terms_and_conditions = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_quotes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Quote {self.quote_number} - {self.customer.get_full_name()}"

    class Meta:
        ordering = ["-quote_date", "-created_at"]


class QuoteItem(models.Model):
    """Line items for quotes"""

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, null=True, blank=True
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        # Calculate line total
        from decimal import Decimal

        subtotal = self.quantity * self.unit_price
        discount = subtotal * (self.discount_percent / Decimal("100"))
        self.line_total = subtotal - discount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"

    class Meta:
        ordering = ["id"]


class Order(models.Model):
    """Sales orders from customers"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("partial", "Partially Paid"),
        ("paid", "Fully Paid"),
        ("overdue", "Overdue"),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders"
    )
    quote = models.ForeignKey(
        Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )

    # Dates
    order_date = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)
    shipped_date = models.DateField(null=True, blank=True)

    # Shipping info
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default="USA")

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Additional info
    purchase_order_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.order_number} - {self.customer.get_full_name()}"

    def update_payment_status(self):
        """Update payment status based on paid amount"""
        if self.paid_amount >= self.total_amount:
            self.payment_status = "paid"
        elif self.paid_amount > 0:
            self.payment_status = "partial"
        else:
            self.payment_status = "unpaid"
        self.balance_due = self.total_amount - self.paid_amount

    class Meta:
        ordering = ["-order_date", "-created_at"]


class OrderItem(models.Model):
    """Line items for orders"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, null=True, blank=True
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Fulfillment tracking
    quantity_shipped = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_delivered = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        # Calculate line total
        from decimal import Decimal

        subtotal = self.quantity * self.unit_price
        discount = subtotal * (self.discount_percent / Decimal("100"))
        self.line_total = subtotal - discount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"

    class Meta:
        ordering = ["id"]


class Invoice(models.Model):
    """Invoices for billing customers"""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("shipped", "Shipped"),
        ("sent", "Sent"),
        ("viewed", "Viewed"),
        ("partial", "Partially Paid"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    DELIVERY_SERVICE_CHOICES = [
        ("usps", "USPS"),
        ("ups", "UPS"),
        ("fedex", "FedEx"),
        ("dhl", "DHL"),
        ("other", "Other"),
    ]

    SHIPPING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("preparing", "Preparing"),
        ("shipped", "Shipped"),
        ("in_transit", "In Transit"),
        ("delivered", "Delivered"),
        ("returned", "Returned"),
        ("cancelled", "Cancelled"),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="invoices",
        null=True,
        blank=True,
    )
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # For shop/anonymous orders
    tracking_code = models.UUIDField(
        null=True, blank=True, unique=True, help_text="For anonymous order tracking"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_invoices",
        help_text="For authenticated shop orders",
    )
    is_shop_order = models.BooleanField(
        default=False, help_text="Indicates if this is from the shop (not admin)"
    )

    # Contact info for anonymous orders
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    # shipping info for shop orders
    delivery_service = models.CharField(
        max_length=20,
        choices=DELIVERY_SERVICE_CHOICES,
        null=True,
        blank=True,
        help_text="Shipping service for shop orders",
    )
    post_tracking_number = models.CharField(
        max_length=50, blank=True, help_text="For shop orders with shipping"
    )

    shipping_status = models.CharField(
        max_length=20,
        choices=SHIPPING_STATUS_CHOICES,
        default="pending",
        help_text="Shipping status for shop orders",
    )

    # Dates
    invoice_date = models.DateField()
    due_date = models.DateField()

    # Billing address
    billing_address_line1 = models.CharField(max_length=255, blank=True)
    billing_address_line2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_postal_code = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=100, default="USA")

    # Shipping address (for shop orders)
    shipping_same_as_billing = models.BooleanField(default=True)
    shipping_address_line1 = models.CharField(max_length=255, blank=True)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=100, default="USA")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Payment terms
    payment_terms = models.CharField(max_length=100, default="Net 30")
    late_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Additional info
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # Email tracking
    sent_date = models.DateTimeField(null=True, blank=True)
    viewed_date = models.DateTimeField(null=True, blank=True)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        import uuid
        from django.utils import timezone

        # Generate invoice number if not set
        if not self.invoice_number:
            if self.is_shop_order:
                # For shop orders, use SO- prefix
                today = timezone.now().strftime("%Y%m%d")
                count = (
                    Invoice.objects.filter(
                        invoice_number__startswith=f"SO-{today}"
                    ).count()
                    + 1
                )
                self.invoice_number = f"SO-{today}-{count:04d}"
            else:
                # For regular invoices, use INV- prefix
                today = timezone.now().strftime("%Y%m%d")
                count = (
                    Invoice.objects.filter(
                        invoice_number__startswith=f"INV-{today}"
                    ).count()
                    + 1
                )
                self.invoice_number = f"INV-{today}-{count:04d}"

        # Generate tracking code for shop orders if not set
        if self.is_shop_order and not self.tracking_code:
            self.tracking_code = uuid.uuid4()

        # Copy billing to shipping if same
        if self.shipping_same_as_billing:
            self.shipping_address_line1 = self.billing_address_line1
            self.shipping_address_line2 = self.billing_address_line2
            self.shipping_city = self.billing_city
            self.shipping_state = self.billing_state
            self.shipping_postal_code = self.billing_postal_code
            self.shipping_country = self.billing_country

        super().save(*args, **kwargs)

    def __str__(self):
        if self.customer:
            return f"Invoice {self.invoice_number} - {self.customer.get_full_name()}"
        elif self.first_name and self.last_name:
            return f"Invoice {self.invoice_number} - {self.first_name} {self.last_name}"
        else:
            return f"Invoice {self.invoice_number}"

    @property
    def is_anonymous(self):
        return self.customer is None and self.user is None

    @property
    def customer_name(self):
        if self.customer:
            return self.customer.get_full_name()
        else:
            return f"{self.first_name} {self.last_name}".strip()

    @property
    def order_number(self):
        """Alias for compatibility with existing shop templates"""
        return self.invoice_number

    @property
    def order_date(self):
        """Alias for compatibility with existing shop templates"""
        return self.invoice_date

    def calculate_totals(self):
        """Calculate invoice totals from items"""
        from decimal import Decimal

        self.subtotal = sum(item.line_total for item in self.items.all()) or Decimal(
            "0"
        )
        self.tax_amount = self.subtotal * (self.tax_rate / Decimal("100"))
        self.total_amount = (
            self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
        )
        self.balance_due = self.total_amount - self.paid_amount
        self.save()

    def update_status(self):
        """Update invoice status based on payments and due date"""
        from django.utils import timezone

        if self.paid_amount >= self.total_amount:
            self.status = "paid"
        elif self.paid_amount > 0:
            self.status = "partial"
        elif self.due_date < timezone.now().date() and self.status not in [
            "cancelled",
            "refunded",
        ]:
            self.status = "overdue"

        self.balance_due = self.total_amount - self.paid_amount

    class Meta:
        ordering = ["-invoice_date", "-created_at"]


class InvoiceItem(models.Model):
    """Line items for invoices"""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, null=True, blank=True
    )
    inventory = models.ForeignKey(
        "product.Inventory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items",
    )
    description = models.CharField(max_length=500)

    # Store selected product options as JSON
    product_options = models.JSONField(default=dict, blank=True)
    # Format: {"Color": "Red", "Size": "Large"}

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        # Calculate line total
        from decimal import Decimal

        subtotal = self.quantity * self.unit_price
        discount = subtotal * (self.discount_percent / Decimal("100"))
        self.line_total = subtotal - discount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"

    def get_options_display(self):
        """Get formatted display of selected options"""
        if not self.product_options:
            return ""
        return ", ".join([f"{k}: {v}" for k, v in self.product_options.items()])

    class Meta:
        ordering = ["id"]


class Payment(models.Model):
    """Payment/collection tracking"""

    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash"),
        ("check", "Check"),
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("bank_transfer", "Bank Transfer"),
        ("paypal", "PayPal"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("cancelled", "Cancelled"),
    ]

    payment_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )

    # Payment details
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Reference info
    reference_number = models.CharField(
        max_length=100, blank=True
    )  # Check number, transaction ID, etc.
    bank_name = models.CharField(max_length=100, blank=True)

    # Additional info
    notes = models.TextField(blank=True)

    # Tracking
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="processed_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        customer_name = self.customer.get_full_name() if self.customer else "Anonymous"
        return f"Payment {self.payment_number} - ${self.amount} from {customer_name}"

    class Meta:
        ordering = ["-payment_date", "-created_at"]


class CreditNote(models.Model):
    """Credit notes for returns/refunds"""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("issued", "Issued"),
        ("applied", "Applied"),
        ("cancelled", "Cancelled"),
    ]

    credit_note_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="credit_notes"
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_notes",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_notes",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Dates
    issue_date = models.DateField()

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    applied_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Reason
    reason = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_credit_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Credit Note {self.credit_note_number} - ${self.total_amount}"

    class Meta:
        ordering = ["-issue_date", "-created_at"]


class CreditNoteItem(models.Model):
    """Line items for credit notes"""

    credit_note = models.ForeignKey(
        CreditNote, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, null=True, blank=True
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"

    class Meta:
        ordering = ["id"]
