from django import forms
from .models import (
    Customer,
    CustomerAddress,
    CustomerContact,
    CustomerNote,
    CustomerDocument,
)


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "company_category",
            "company_name",
            "first_name",
            "last_name",
            "email",
            "phone",
            "internal_notes",
        ]
        widgets = {
            "company_category": forms.Select(attrs={"class": "form-control"}),
            "company_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Company Name"}
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "First Name",
                    "required": True,
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Last Name",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email Address",
                    "required": True,
                }
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone Number"}
            ),
            "internal_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Additional notes...",
                }
            ),
        }


class CustomerAddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = [
            "address_type",
            "label",
            "recipient_name",
            "company_name",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
            "is_default",
        ]
        widgets = {
            "address_type": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "label": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Home, Office, Warehouse",
                }
            ),
            "recipient_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Full name of recipient",
                    "required": True,
                }
            ),
            "company_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Company name (optional)",
                }
            ),
            "address_line1": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Street address",
                    "required": True,
                }
            ),
            "address_line2": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Apartment, suite, unit, etc. (optional)",
                }
            ),
            "city": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "City", "required": True}
            ),
            "state": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "State/Province",
                    "required": True,
                }
            ),
            "postal_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "ZIP/Postal code",
                    "required": True,
                }
            ),
            "country": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Country",
                    "required": True,
                }
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+1234567890"}
            ),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes for better styling
        for field_name, field in self.fields.items():
            if field_name == "is_default":
                field.widget.attrs["class"] = (
                    "h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                )
            else:
                field.widget.attrs["class"] = (
                    "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                )


class CustomerContactForm(forms.ModelForm):
    class Meta:
        model = CustomerContact
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "job_title",
            "department",
            "is_primary",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "First Name",
                    "required": True,
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Last Name",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email Address",
                    "required": True,
                }
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone Number"}
            ),
            "job_title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Job Title"}
            ),
            "department": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Department"}
            ),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add DaisyUI classes
        for field_name, field in self.fields.items():
            if field_name == "is_primary":
                field.widget.attrs["class"] = "checkbox checkbox-primary"
            else:
                field.widget.attrs["class"] = "input input-bordered w-full"


class CustomerNoteForm(forms.ModelForm):
    class Meta:
        model = CustomerNote
        fields = ["note"]
        widgets = {
            "note": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "rows": 4,
                    "placeholder": "Add a note about this customer...",
                    "required": True,
                }
            )
        }


class CustomerDocumentForm(forms.ModelForm):
    class Meta:
        model = CustomerDocument
        fields = ["document", "description"]
        widgets = {
            "document": forms.FileInput(
                attrs={
                    "class": "file-input file-input-bordered w-full",
                    "required": True,
                }
            ),
            "description": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "Brief description of the document",
                }
            ),
        }
