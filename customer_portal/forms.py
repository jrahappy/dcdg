from django import forms
from customer.models import Customer, CustomerAddress


class CompanyInfoForm(forms.ModelForm):
    """Form for editing company information only"""
    class Meta:
        model = Customer
        fields = [
            'company_name', 'internal_notes'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter your company name'
            }),
            'internal_notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered h-24',
                'rows': 4,
                'placeholder': 'Add any additional notes or special instructions'
            }),
        }
        labels = {
            'company_name': 'Company Name',
            'internal_notes': 'Internal Notes',
        }
        help_texts = {
            'company_name': 'The official name of your company or business',
            'internal_notes': 'These notes are for internal reference only',
        }


class ProfileForm(forms.ModelForm):
    """Form for editing customer profile"""
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'email', 'phone'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
        }


class AddressForm(forms.ModelForm):
    """Form for managing shipping/billing addresses"""
    class Meta:
        model = CustomerAddress
        fields = [
            'address_type', 'label', 'recipient_name', 'company_name',
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'phone', 'is_default'
        ]
        widgets = {
            'address_type': forms.Select(attrs={'class': 'form-control'}),
            'label': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Home, Office, Warehouse'
            }),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'value': 'United States'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }