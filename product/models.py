from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify

User = get_user_model()


class Category(models.Model):
    """Hierarchical category model for products"""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50, blank=True, help_text="Icon class name (e.g., fas fa-tooth)"
    )
    cover_image = models.ImageField(upload_to="category_covers/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["order", "name"]
        unique_together = [["parent", "slug"]]

    def __str__(self):
        if self.parent:
            return f"{self.get_full_path()}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure unique slug within same parent
            original_slug = self.slug
            counter = 1
            while (
                Category.objects.filter(slug=self.slug, parent=self.parent)
                .exclude(pk=self.pk)
                .exists()
            ):
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_full_path(self):
        """Get the full category path from root to current"""
        path_parts = [self.name]
        parent = self.parent
        while parent:
            path_parts.insert(0, parent.name)
            parent = parent.parent
        return " > ".join(path_parts)

    def get_ancestors(self):
        """Get all ancestor categories"""
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.insert(0, parent)
            parent = parent.parent
        return ancestors

    def get_descendants(self):
        """Get all descendant categories"""
        descendants = []
        children = list(self.children.all())
        for child in children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_level(self):
        """Get the depth level of this category (0 for root)"""
        level = 0
        parent = self.parent
        while parent:
            level += 1
            parent = parent.parent
        return level

    def get_root(self):
        """Get the root category of this branch"""
        if not self.parent:
            return self
        parent = self.parent
        while parent.parent:
            parent = parent.parent
        return parent

    def is_leaf(self):
        """Check if this category has no children"""
        return not self.children.exists()

    def get_product_count(self, include_descendants=True):
        """Get count of products in this category"""
        count = self.products.filter(status="active").count()
        if include_descendants:
            for child in self.get_descendants():
                count += child.products.filter(status="active").count()
        return count


class Product(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("discontinued", "Discontinued"),
        ("draft", "Draft"),
    ]

    # Basic Information
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    sku = models.CharField(
        max_length=50, unique=True, blank=True, help_text="Stock Keeping Unit"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Product category",
    )
    brand = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)

    supplier = models.ForeignKey(
        "purchases.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Supplier for this product",
    )
    # Description
    short_description = models.CharField(
        max_length=255, help_text="Brief description for listings"
    )
    long_description = models.TextField(help_text="Detailed product description")
    features = models.TextField(blank=True, help_text="Product features (one per line)")
    specifications = models.JSONField(
        default=dict,
        blank=True,
        help_text="Technical specifications as key-value pairs",
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        help_text="Cost price for margin calculations",
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Inventory
    quantity_in_stock = models.IntegerField(
        default=0, validators=[MinValueValidator(0)]
    )
    minimum_stock_level = models.IntegerField(
        default=5,
        validators=[MinValueValidator(0)],
        help_text="Alert when stock falls below this level",
    )
    weight = models.DecimalField(
        max_digits=10, decimal_places=3, blank=True, null=True, help_text="Weight in kg"
    )
    dimensions = models.CharField(
        max_length=100, blank=True, help_text="L x W x H in cm"
    )

    # Images
    main_image = models.ImageField(upload_to="products/main/", blank=True, null=True)
    thumbnail_image = models.ImageField(
        upload_to="products/thumbnails/", blank=True, null=True
    )

    # Status and Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_featured = models.BooleanField(default=False)
    tags = models.CharField(
        max_length=500, blank=True, help_text="Comma-separated tags"
    )

    # Tracking
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="products_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.IntegerField(default=0)
    is_serial_number_managed = models.BooleanField(
        default=False, help_text="Whether this product requires serial number tracking"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure unique slug
            original_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    @property
    def display_price(self):
        """Price after discount"""
        if self.discount_percentage > 0:
            discount_amount = self.price * (self.discount_percentage / 100)
            return self.price - discount_amount
        return self.price

    @property
    def margin_percentage(self):
        """Calculate profit margin percentage"""
        if self.cost and self.cost > 0:
            margin = ((self.price - self.cost) / self.cost) * 100
            return round(margin, 2)
        return None

    @property
    def is_low_stock(self):
        """Check if stock is below minimum level"""
        return self.quantity_in_stock <= self.minimum_stock_level

    @property
    def feature_list(self):
        """Return features as a list"""
        if self.features:
            return [f.strip() for f in self.features.split("\n") if f.strip()]
        return []

    @property
    def tag_list(self):
        """Return tags as a list"""
        if self.tags:
            return [t.strip() for t in self.tags.split(",") if t.strip()]
        return []


class ProductDoc(models.Model):
    DOC_TYPE_CHOICES = [
        ("manual", "User Manual"),
        ("spec_sheet", "Specification Sheet"),
        ("brochure", "Brochure"),
        ("warranty", "Warranty Information"),
        ("installation", "Installation Guide"),
        ("safety", "Safety Data Sheet"),
        ("certificate", "Certificate"),
        ("other", "Other"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="documents"
    )
    title = models.CharField(max_length=200)
    doc_type = models.CharField(
        max_length=20, choices=DOC_TYPE_CHOICES, default="other"
    )
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to="products/documents/", help_text="PDF, DOC, DOCX files allowed"
    )
    file_size = models.IntegerField(
        blank=True, null=True, help_text="File size in bytes"
    )
    is_public = models.BooleanField(
        default=True, help_text="Whether this document is publicly accessible"
    )
    download_count = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="product_docs_uploaded"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["doc_type", "title"]
        verbose_name = "Product Document"
        verbose_name_plural = "Product Documents"

    def __str__(self):
        return f"{self.product.name} - {self.title}"

    def save(self, *args, **kwargs):
        # Store file size
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None

    @property
    def file_extension(self):
        """Return file extension"""
        if self.file:
            return self.file.name.split(".")[-1].upper()
        return None


class ProductImage(models.Model):
    """Additional product images"""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/gallery/")
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "uploaded_at"]
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"


class Inventory(models.Model):
    """Track individual product items with serial numbers and warranty"""

    STATUS_CHOICES = [
        ("available", "Available"),
        ("sold", "Sold"),
        ("reserved", "Reserved"),
        ("returned", "Returned"),
        ("defective", "Defective"),
        ("in_repair", "In Repair"),
        ("lost", "Lost"),
        ("disposed", "Disposed"),
    ]

    WARRANTY_STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("void", "Void"),
        ("extended", "Extended"),
        ("na", "Not Applicable"),
    ]

    # Product Information
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="inventory_items"
    )
    serial_number = models.CharField(
        max_length=100, unique=True, help_text="Unique serial number for this item"
    )
    batch_number = models.CharField(
        max_length=50, blank=True, help_text="Manufacturing batch/lot number"
    )

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="available"
    )
    condition = models.CharField(
        max_length=50, default="New", help_text="e.g., New, Refurbished, Used"
    )

    # Purchase Information
    purchase_date = models.DateField(
        blank=True, null=True, help_text="Date when item was purchased/received"
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Purchase price for this specific item",
    )
    supplier = models.CharField(
        max_length=200, blank=True, help_text="Supplier/vendor name"
    )
    purchase_order_number = models.CharField(
        max_length=50, blank=True, help_text="PO number for tracking"
    )

    # Warranty Information
    warranty_start_date = models.DateField(
        blank=True,
        null=True,
        help_text="Warranty start date (usually purchase/activation date)",
    )
    warranty_end_date = models.DateField(
        blank=True, null=True, help_text="Warranty expiration date"
    )
    warranty_status = models.CharField(
        max_length=20, choices=WARRANTY_STATUS_CHOICES, default="na"
    )
    warranty_provider = models.CharField(
        max_length=200,
        blank=True,
        help_text="Warranty provider (manufacturer, third-party, etc.)",
    )
    warranty_terms = models.TextField(
        blank=True, help_text="Specific warranty terms and conditions"
    )
    extended_warranty_end_date = models.DateField(
        blank=True,
        null=True,
        help_text="Extended warranty expiration date if applicable",
    )

    # Location and Assignment
    current_location = models.CharField(
        max_length=200, blank=True, help_text="Current physical location of the item"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_inventory",
        help_text="User/customer this item is assigned to",
    )
    assigned_date = models.DateTimeField(
        blank=True, null=True, help_text="Date when item was assigned"
    )

    # Customer Information (if sold)
    customer = models.ForeignKey(
        "customer.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchased_items",
        help_text="Customer who purchased this item",
    )
    sale_date = models.DateField(
        blank=True, null=True, help_text="Date when item was sold"
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Actual sale price for this item",
    )

    # Service and Maintenance
    last_service_date = models.DateField(
        blank=True, null=True, help_text="Last service/maintenance date"
    )
    next_service_date = models.DateField(
        blank=True, null=True, help_text="Next scheduled service date"
    )
    service_history = models.TextField(
        blank=True, help_text="Service and repair history"
    )

    # Additional Information
    notes = models.TextField(blank=True, help_text="Additional notes about this item")
    barcode = models.CharField(
        max_length=100, blank=True, help_text="Barcode for scanning"
    )
    qr_code = models.CharField(max_length=200, blank=True, help_text="QR code data")

    # Tracking
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="inventory_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        indexes = [
            models.Index(fields=["serial_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["product", "status"]),
            models.Index(fields=["warranty_end_date"]),
        ]

    def __str__(self):
        return f"{self.product.name} - SN: {self.serial_number}"

    @property
    def is_under_warranty(self):
        """Check if item is currently under warranty"""
        from datetime import date

        if self.warranty_end_date:
            return date.today() <= self.warranty_end_date
        return False

    @property
    def warranty_days_remaining(self):
        """Calculate days remaining in warranty"""
        from datetime import date

        if self.warranty_end_date and self.is_under_warranty:
            delta = self.warranty_end_date - date.today()
            return delta.days
        return 0

    @property
    def age_in_days(self):
        """Calculate age of item since purchase"""
        from datetime import date

        if self.purchase_date:
            delta = date.today() - self.purchase_date
            return delta.days
        return None

    @property
    def profit_margin(self):
        """Calculate profit margin if sold"""
        if self.sale_price and self.purchase_price:
            margin = (
                (self.sale_price - self.purchase_price) / self.purchase_price
            ) * 100
            return round(margin, 2)
        return None

    def update_warranty_status(self):
        """Update warranty status based on dates"""
        from datetime import date

        today = date.today()

        if not self.warranty_end_date:
            self.warranty_status = "na"
        elif (
            self.extended_warranty_end_date and today <= self.extended_warranty_end_date
        ):
            self.warranty_status = "extended"
        elif today <= self.warranty_end_date:
            self.warranty_status = "active"
        else:
            self.warranty_status = "expired"

        self.save(update_fields=["warranty_status"])

    def calculate_warranty_end_date(self, warranty_months=12):
        """Calculate warranty end date from start date"""
        from dateutil.relativedelta import relativedelta

        if self.warranty_start_date:
            self.warranty_end_date = self.warranty_start_date + relativedelta(
                months=warranty_months
            )
            self.save(update_fields=["warranty_end_date"])


class ProductOption(models.Model):
    """Model for product options (e.g., size, color)"""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="options",
        help_text="The product this option belongs to",
    )
    option_name = models.ForeignKey(
        "ProductOptionName",
        on_delete=models.CASCADE,
        related_name="product_options",
        help_text="The name of the option (e.g., Size, Color)",
    )
    option_ordering = models.IntegerField(
        default=0, help_text="Display order of this option for the product"
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this option is active for the product"
    )
    created_at = models.DateTimeField(auto_now_add=True)


class ProductOptionName(models.Model):
    """Model for product option names (e.g., Color, Size)"""

    name = models.CharField(
        max_length=100, unique=True, help_text="Name of the option (e.g., Size, Color)"
    )
    description = models.TextField(
        blank=True, help_text="Description of this option type"
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this option is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Option Name"
        verbose_name_plural = "Product Option Names"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductOptionItem(models.Model):
    """Model for individual product option items (e.g., Large, Red)"""

    option_name = models.ForeignKey(
        ProductOptionName,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The option this item belongs to",
    )
    value = models.CharField(
        max_length=20, help_text="Value of the option item (e.g., Large, Red)"
    )
    ordering = models.IntegerField(
        default=0, help_text="Display order of this option item"
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this option item is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Option Item"
        verbose_name_plural = "Product Option Items"
        ordering = ["ordering", "value"]

    def __str__(self):
        return f"{self.option_name.name}: {self.value}"

    def save(self, *args, **kwargs):
        # Ensure unique value for each option name
        if (
            ProductOptionItem.objects.filter(
                option_name=self.option_name, value=self.value
            )
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValueError(
                f"Option item '{self.value}' already exists for '{self.option_name.name}'"
            )
        super().save(*args, **kwargs)
