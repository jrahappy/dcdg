from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'company_name',
            'first_name',
            'last_name',
            'email',
            'phone',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'country',
            'notes',
            'is_active'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address', 'required': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 1'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 2'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country', 'value': 'USA'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }