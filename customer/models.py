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
