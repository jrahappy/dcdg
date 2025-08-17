from django import forms
from django.utils import timezone
from decimal import Decimal
from .models import Expense, LedgerAccount
from customer.models import FinancialAccount
from purchases.models import Supplier


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'expense_date',
            'vendor_name',
            'category',
            'description',
            'amount',
            'tax_amount',
            'reference_number',
            'payment_method',
            'status',
            'notes',
            'receipt_file',
        ]
        widgets = {
            'expense_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'input input-bordered w-full',
                'value': timezone.now().date()
            }),
            'vendor_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter vendor/supplier name'
            }),
            'category': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'description': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Brief description of expense'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'tax_amount': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'value': '0.00'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Invoice/Receipt number (optional)'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'status': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Additional notes (optional)'
            }),
            'receipt_file': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full'
            }),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Make optional fields not required
        self.fields['reference_number'].required = False
        self.fields['payment_method'].required = False
        self.fields['receipt_file'].required = False
        self.fields['notes'].required = False
        self.fields['tax_amount'].initial = Decimal('0.00')

    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure vendor_name is provided
        vendor_name = cleaned_data.get('vendor_name')
        if not vendor_name:
            raise forms.ValidationError("Please enter a vendor name.")
        
        # Ensure amounts are Decimal
        amount = cleaned_data.get('amount')
        if amount is not None:
            cleaned_data['amount'] = Decimal(str(amount))
        
        tax_amount = cleaned_data.get('tax_amount')
        if tax_amount is not None:
            cleaned_data['tax_amount'] = Decimal(str(tax_amount))
        else:
            cleaned_data['tax_amount'] = Decimal('0.00')
        
        return cleaned_data