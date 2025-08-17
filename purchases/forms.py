from django import forms
from django.forms import inlineformset_factory
from .models import PurchaseOrder, PurchaseOrderItem, SupplierPayment
from product.models import Product
from datetime import date, datetime
from decimal import Decimal


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'order_number', 'supplier', 'status', 'order_date', 'expected_delivery_date',
            'tax_rate', 'shipping_cost', 'discount_percent',
            'reference_number', 'notes', 'internal_notes'
        ]
        widgets = {
            'order_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'PO-YYYYMMDD-001'
            }),
            'supplier': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'status': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'order_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
            'expected_delivery_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'shipping_cost': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': "Supplier's reference number"
            }),
            'notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Notes visible to supplier'
            }),
            'internal_notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Internal notes (not visible to supplier)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            # Set default order date to today for new orders
            self.fields['order_date'].initial = date.today()
            # Generate order number
            today = date.today()
            # Count existing orders for today
            count = PurchaseOrder.objects.filter(
                order_number__startswith=f"PO-{today.strftime('%Y%m%d')}"
            ).count() + 1
            self.fields['order_number'].initial = f"PO-{today.strftime('%Y%m%d')}-{count:03d}"


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'description', 'quantity', 'unit_cost']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'updateItemDescription(this)'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Item description'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'onchange': 'calculateLineTotal(this)'
            }),
            'unit_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'onchange': 'calculateLineTotal(this)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show products that can be ordered
        self.fields['product'].queryset = Product.objects.filter(
            status__in=['active', 'draft']
        ).order_by('name')


# Create formset for purchase order items
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class SupplierPaymentForm(forms.ModelForm):
    """Form for recording supplier payments"""
    
    PAYMENT_METHOD_CHOICES = [
        ('', '--- Select Payment Method ---'),
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('wire', 'Wire Transfer'),
        ('credit_card', 'Credit Card'),
        ('ach', 'ACH Transfer'),
        ('other', 'Other'),
    ]
    
    method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        })
    )
    
    class Meta:
        model = SupplierPayment
        fields = ['date', 'amount', 'method', 'is_advance']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'input input-bordered w-full',
                'value': date.today().strftime('%Y-%m-%d')
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter payment amount'
            }),
            'is_advance': forms.CheckboxInput(attrs={
                'class': 'checkbox'
            })
        }
        labels = {
            'is_advance': 'This is an advance payment (prepayment)'
        }
    
    def __init__(self, *args, **kwargs):
        self.purchase_order = kwargs.pop('purchase_order', None)
        super().__init__(*args, **kwargs)
        
        if self.purchase_order:
            # Set the initial amount to the remaining balance
            if hasattr(self.purchase_order, 'get_balance_due'):
                self.fields['amount'].initial = self.purchase_order.get_balance_due()
            else:
                # Calculate balance due if method doesn't exist
                from django.db.models import Sum
                total_paid = SupplierPayment.objects.filter(
                    purchase_order=self.purchase_order,
                    status='APPROVED'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                balance = self.purchase_order.total_amount - total_paid
                self.fields['amount'].initial = max(balance, Decimal('0'))
    
    def save(self, commit=True):
        payment = super().save(commit=False)
        
        if self.purchase_order:
            payment.purchase_order = self.purchase_order
            payment.supplier = self.purchase_order.supplier
        
        # Always set company - get or create default
        if not hasattr(payment, 'company') or not payment.company:
            from customer.models import Organization
            try:
                payment.company = Organization.objects.first()
                if not payment.company:
                    payment.company = Organization.objects.create(
                        name="Default Company",
                        code="DEFAULT"
                    )
            except:
                payment.company = Organization.objects.create(
                    name="Default Company",
                    code="DEFAULT"
                )
        
        # Default to approved status for immediate posting
        payment.status = 'APPROVED'
        
        if commit:
            payment.save()
            
        return payment