from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone

User = get_user_model()


class Organization(models.Model):
    """
    Represents an internal organization for admin/staff management only.
    NOT for customer use - this is for internal tracking and organization
    of admin/staff users within the dental support organization.
    """

    ORGANIZATION_TYPE_CHOICES = [
        ("dental_practice", "Dental Practice"),
        ("supplier", "Supplier"),
        ("laboratory", "Laboratory"),
        ("distributor", "Distributor"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=255, unique=True)
    organization_type = models.CharField(
        max_length=20, choices=ORGANIZATION_TYPE_CHOICES, default="dental_practice"
    )
    tax_id = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    # Contact Information
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True)

    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="United States", blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    lock_until = models.DateField(
        blank=True, null=True
    )  # 마감 잠금(이 날짜 이하 전기 금지)

    class Meta:
        ordering = ["name"]
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        address_parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ]
        return ", ".join(part for part in address_parts if part)

    @property
    def member_count(self):
        """Get count of active users in this organization"""
        return self.users.filter(is_active=True).count()


class Customer(models.Model):
    """
    Represents a customer in the system.
    Organization field is for internal admin/staff use only to group
    and manage admin/staff users - NOT for customer organizations.
    """

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Administrator"),
        ("manager", "Manager"),
        ("staff", "Staff"),
        ("customer", "Customer"),
    ]

    company_category_choices = [
        ("supplier", "Supplier"),
        ("retailer", "Retailer"),
        ("customer", "Customer"),
        ("wholesaler", "Wholesaler"),
    ]

    # Changed from OneToOneField to ForeignKey to allow multiple customers per user
    # But typically one user = one customer
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer",
        null=True,
        blank=True,
    )

    company_category = models.CharField(
        max_length=20, choices=company_category_choices, default="customer"
    )
    company_name = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    profile_image = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        help_text="Profile picture"
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        if self.company_name:
            return f"{self.company_name} - {self.get_full_name()}"
        return self.get_full_name()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def get_default_address(self):
        """Get the default address for this customer"""
        return self.addresses.filter(is_default=True, is_active=True).first()

    @property
    def get_billing_address(self):
        """Get the default billing address"""
        from django.db.models import Q

        return self.addresses.filter(
            Q(address_type="billing") | Q(address_type="both"),
            is_default=True,
            is_active=True,
        ).first()

    @property
    def get_shipping_address(self):
        """Get the default shipping address"""
        from django.db.models import Q

        return self.addresses.filter(
            Q(address_type="shipping") | Q(address_type="both"),
            is_default=True,
            is_active=True,
        ).first()

    @property
    def display_name(self):
        """Display name with organization if available"""
        if self.user and self.user.organization:
            return f"{self.get_full_name()} ({self.user.organization.name})"
        elif self.company_name:
            return f"{self.get_full_name()} ({self.company_name})"
        return self.get_full_name()


class CustomerAddress(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ("billing", "Billing Address"),
        ("shipping", "Shipping Address"),
        ("both", "Both Billing & Shipping"),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="addresses"
    )
    # Optional user link for registered shop customers
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_addresses",
        null=True,
        blank=True,
    )
    address_type = models.CharField(
        max_length=10, choices=ADDRESS_TYPE_CHOICES, default="shipping"
    )
    label = models.CharField(
        max_length=100, help_text="e.g., Home, Office, Warehouse", blank=True
    )
    recipient_name = models.CharField(
        max_length=200, help_text="Name of the person receiving at this address"
    )
    company_name = models.CharField(max_length=255, blank=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="United States")
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text="Contact phone for this address",
    )
    is_default = models.BooleanField(
        default=False, help_text="Set as default address for this type"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name = "Customer Address"
        verbose_name_plural = "Customer Addresses"
        indexes = [
            models.Index(fields=["customer", "address_type", "is_default"]),
        ]

    def __str__(self):
        label = f" ({self.label})" if self.label else ""
        return f"{self.get_address_type_display()}{label} - {self.recipient_name}"

    @property
    def full_address(self):
        address_parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ]
        return ", ".join(part for part in address_parts if part)

    def save(self, *args, **kwargs):
        # If this is set as default, unset other defaults for same customer and type
        if self.is_default:
            if self.address_type == "both":
                # Unset all other defaults for this customer
                CustomerAddress.objects.filter(
                    customer=self.customer, is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
            else:
                # Unset other defaults for same type or 'both' type
                CustomerAddress.objects.filter(
                    customer=self.customer,
                    address_type__in=[self.address_type, "both"],
                    is_default=True,
                ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)


class CustomerContact(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="contacts"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "last_name", "first_name"]
        verbose_name = "Customer Contact"
        verbose_name_plural = "Customer Contacts"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class CustomerNote(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="notes"
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Customer Note"
        verbose_name_plural = "Customer Notes"


class CustomerDocument(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="documents"
    )
    document = models.FileField(upload_to="customer_documents/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class FinancialAccount(models.Model):
    """
    Represents both bank accounts and credit cards for an organization.
    Used for accounting purposes and payment processing.
    """
    
    ACCOUNT_TYPE_CHOICES = [
        ("checking", "Checking Account"),
        ("savings", "Savings Account"),
        ("credit_card", "Credit Card"),
        ("debit_card", "Debit Card"),
        ("line_of_credit", "Line of Credit"),
        ("merchant", "Merchant Account"),
        ("other", "Other"),
    ]
    
    CARD_NETWORK_CHOICES = [
        ("visa", "Visa"),
        ("mastercard", "Mastercard"),
        ("amex", "American Express"),
        ("discover", "Discover"),
        ("other", "Other"),
    ]
    
    # Relationship
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name="financial_accounts"
    )
    
    # Basic Information
    account_type = models.CharField(
        max_length=20, 
        choices=ACCOUNT_TYPE_CHOICES,
        help_text="Type of financial account"
    )
    account_name = models.CharField(
        max_length=255,
        help_text="Friendly name for this account (e.g., 'Main Checking', 'Company Visa')"
    )
    
    # Bank Information
    bank_name = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Name of the bank or financial institution"
    )
    routing_number = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Bank routing number (for ACH/wire transfers)"
    )
    account_number = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Bank account or card number (store securely)"
    )
    
    # Credit Card Specific
    card_network = models.CharField(
        max_length=20,
        choices=CARD_NETWORK_CHOICES,
        blank=True,
        help_text="Credit card network (for credit/debit cards)"
    )
    card_last_four = models.CharField(
        max_length=4,
        blank=True,
        help_text="Last 4 digits of card number"
    )
    card_expiry_month = models.IntegerField(
        null=True,
        blank=True,
        help_text="Card expiry month (1-12)"
    )
    card_expiry_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Card expiry year (YYYY)"
    )
    cardholder_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name on the card"
    )
    
    # Account Details
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="Currency code (e.g., USD, EUR)"
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Credit limit for credit cards/lines of credit"
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current balance (optional, for tracking)"
    )
    
    # Accounting Integration
    ledger_account = models.ForeignKey(
        "accounting.LedgerAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_accounts",
        help_text="Linked general ledger account for accounting"
    )
    
    # Additional Information
    swift_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="SWIFT/BIC code for international transfers"
    )
    iban = models.CharField(
        max_length=50,
        blank=True,
        help_text="International Bank Account Number"
    )
    
    # Status and Metadata
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary account for this type"
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-is_primary", "account_type", "account_name"]
        verbose_name = "Financial Account"
        verbose_name_plural = "Financial Accounts"
        indexes = [
            models.Index(fields=["organization", "account_type", "is_active"]),
        ]
    
    def __str__(self):
        if self.account_type == "credit_card" and self.card_last_four:
            return f"{self.account_name} (****{self.card_last_four})"
        return self.account_name
    
    @property
    def is_bank_account(self):
        """Check if this is a bank account (checking/savings)"""
        return self.account_type in ["checking", "savings"]
    
    @property
    def is_card(self):
        """Check if this is a card (credit/debit)"""
        return self.account_type in ["credit_card", "debit_card"]
    
    @property
    def display_number(self):
        """Display safe version of account/card number"""
        if self.is_card and self.card_last_four:
            return f"****{self.card_last_four}"
        elif self.account_number:
            # Show last 4 digits of account number
            return f"****{self.account_number[-4:]}" if len(self.account_number) >= 4 else "****"
        return "****"
    
    def save(self, *args, **kwargs):
        # If this is set as primary, unset other primary accounts of same type
        if self.is_primary:
            FinancialAccount.objects.filter(
                organization=self.organization,
                account_type=self.account_type,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        super().save(*args, **kwargs)
