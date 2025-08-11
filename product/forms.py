from django import forms
from django_summernote.widgets import SummernoteWidget
from .models import (
    Product,
    ProductDoc,
    ProductImage,
    Inventory,
    Category,
    ProductOptionName,
    ProductOption,
)
import json


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "category",
            "supplier",
            "brand",
            "manufacturer",
            "short_description",
            "long_description",
            "features",
            "price",
            "cost",
            "discount_percentage",
            "quantity_in_stock",
            "minimum_stock_level",
            "weight",
            "dimensions",
            "status",
            "is_featured",
            "tags",
            "is_serial_number_managed",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Enter product name",
                }
            ),
            "sku": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Stock Keeping Unit",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "supplier": forms.Select(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "brand": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "manufacturer": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "short_description": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Brief description for listings",
                }
            ),
            "long_description": SummernoteWidget(),
            "features": forms.Textarea(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "rows": 3,
                    "placeholder": "Enter features (one per line)",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "cost": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "discount_percentage": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),
            "quantity_in_stock": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "min": "0",
                }
            ),
            "minimum_stock_level": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "min": "0",
                }
            ),
            "weight": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "step": "0.001",
                    "min": "0",
                    "placeholder": "Weight in kg",
                }
            ),
            "dimensions": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "L x W x H in cm",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "is_featured": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                }
            ),
            "tags": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Comma-separated tags",
                }
            ),
            "is_serial_number_managed": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                }
            ),
        }

    specifications = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                "rows": 4,
                "placeholder": 'Enter specifications as JSON (e.g., {"voltage": "220V", "power": "1000W"})',
            }
        ),
        help_text="Technical specifications as JSON key-value pairs",
    )

    product_options = forms.ModelMultipleChoiceField(
        queryset=ProductOptionName.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "checkbox space-y-2"}),
        help_text="Select which options should be available for this product",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Convert specifications dict to JSON string for display
            if self.instance.specifications:
                self.fields["specifications"].initial = json.dumps(
                    self.instance.specifications, indent=2
                )
            # Get selected options for this product
            selected_options = ProductOption.objects.filter(
                product=self.instance
            ).values_list("option_name", flat=True)
            self.fields["product_options"].initial = selected_options

    def clean_specifications(self):
        specifications = self.cleaned_data.get("specifications", "")
        if specifications:
            try:
                # Parse JSON string to dict
                return json.loads(specifications)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for specifications")
        return {}


class ProductSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm",
                "placeholder": "Search products...",
            }
        ),
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.filter(is_active=True),
        empty_label="All Categories",
        widget=forms.Select(
            attrs={
                "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            }
        ),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All Status")] + Product.STATUS_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            }
        ),
    )
    is_featured = forms.ChoiceField(
        required=False,
        choices=[("", "All"), ("true", "Featured Only"), ("false", "Non-Featured")],
        widget=forms.Select(
            attrs={
                "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            }
        ),
    )


class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = [
            "product",
            "serial_number",
            "batch_number",
            "status",
            "condition",
            "purchase_date",
            "purchase_price",
            "supplier",
            "purchase_order_number",
            "warranty_start_date",
            "warranty_end_date",
            "warranty_status",
            "warranty_provider",
            "warranty_terms",
            "extended_warranty_end_date",
            "current_location",
            "assigned_to",
            "customer",
            "sale_date",
            "sale_price",
            "last_service_date",
            "next_service_date",
            "service_history",
            "notes",
            "barcode",
            "qr_code",
        ]
        widgets = {
            "product": forms.Select(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "serial_number": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Unique serial number",
                }
            ),
            "batch_number": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Manufacturing batch/lot number",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "condition": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "e.g., New, Refurbished, Used",
                }
            ),
            "purchase_date": forms.DateInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "type": "date",
                }
            ),
            "purchase_price": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "supplier": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Supplier/vendor name",
                }
            ),
            "purchase_order_number": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "PO number",
                }
            ),
            "warranty_start_date": forms.DateInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "type": "date",
                }
            ),
            "warranty_end_date": forms.DateInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "type": "date",
                }
            ),
            "warranty_status": forms.Select(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "warranty_provider": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Warranty provider",
                }
            ),
            "warranty_terms": forms.Textarea(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "rows": 3,
                }
            ),
            "extended_warranty_end_date": forms.DateInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "type": "date",
                }
            ),
            "current_location": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Current physical location",
                }
            ),
            "assigned_to": forms.Select(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "customer": forms.Select(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "sale_date": forms.DateInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "type": "date",
                }
            ),
            "sale_price": forms.NumberInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "last_service_date": forms.DateInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "type": "date",
                }
            ),
            "next_service_date": forms.DateInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "type": "date",
                }
            ),
            "service_history": forms.Textarea(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "rows": 3,
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "rows": 3,
                }
            ),
            "barcode": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "Barcode for scanning",
                }
            ),
            "qr_code": forms.TextInput(
                attrs={
                    "class": "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500",
                    "placeholder": "QR code data",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show products that have serial number management enabled
        self.fields["product"].queryset = Product.objects.filter(
            is_serial_number_managed=True
        ).order_by("name")

        # Make certain fields optional based on status
        if self.instance and self.instance.pk:
            if self.instance.status != "sold":
                self.fields["customer"].required = False
                self.fields["sale_date"].required = False
                self.fields["sale_price"].required = False


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            "name",
            "parent",
            "description",
            "icon",
            "order",
            "is_active",
            "cover_image",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Enter category name",
                }
            ),
            "parent": forms.Select(
                attrs={
                    "class": "select select-bordered w-full"
                }
            ),
            "description": SummernoteWidget(),
            "icon": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "fas fa-folder",
                }
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "min": "0",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "checkbox checkbox-primary"
                }
            ),
            "cover_image": forms.FileInput(
                attrs={
                    "class": "file-input file-input-bordered w-full",
                    "accept": "image/*",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get all categories except self and its descendants for parent selection
        if self.instance and self.instance.pk:
            # Exclude self and descendants from parent choices
            excluded_ids = [self.instance.pk]
            # get_descendants() returns a list of Category objects, not a QuerySet
            descendants = self.instance.get_descendants()
            excluded_ids.extend([cat.pk for cat in descendants])
            self.fields['parent'].queryset = Category.objects.exclude(pk__in=excluded_ids)
        else:
            self.fields['parent'].queryset = Category.objects.all()
        
        # Make parent field optional
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = "None (Top Level)"
