from django import forms
from django.forms import inlineformset_factory
from .models import Quote, QuoteItem, Order, OrderItem, Invoice, InvoiceItem, Payment, InvoiceShipment, ShipmentItem
from customer.models import Customer
from product.models import Product


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = [
            'quote_number', 'customer', 'status', 'quote_date', 'valid_until',
            'tax_rate', 'discount_percent', 'terms_and_conditions', 'notes'
        ]
        widgets = {
            'quote_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'valid_until': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'quote_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Q-2024-001'
            }),
            'customer': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'placeholder': '8.25'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'terms_and_conditions': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 4
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3
            }),
        }


class QuoteItemForm(forms.ModelForm):
    class Meta:
        model = QuoteItem
        fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0.01'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
        }


QuoteItemFormSet = inlineformset_factory(
    Quote, QuoteItem,
    form=QuoteItemForm,
    extra=1,
    can_delete=True
)


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'order_number', 'customer', 'quote', 'status', 'payment_status',
            'order_date', 'delivery_date', 'shipping_address_line1', 
            'shipping_address_line2', 'shipping_city', 'shipping_state',
            'shipping_postal_code', 'shipping_country', 'shipping_cost',
            'tax_rate', 'discount_percent', 'purchase_order_number',
            'notes', 'internal_notes'
        ]
        widgets = {
            'order_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'delivery_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'order_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'ORD-2024-001'
            }),
            'customer': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'quote': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'payment_status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'shipping_address_line1': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'shipping_address_line2': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'shipping_city': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'shipping_state': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'shipping_postal_code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'shipping_country': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'shipping_cost': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'placeholder': '8.25'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'purchase_order_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3
            }),
            'internal_notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3
            }),
        }


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0.01'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
        }


OrderItemFormSet = inlineformset_factory(
    Order, OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True
)


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'customer', 'order', 'status', 'invoice_date',
            'due_date', 'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_state', 'billing_postal_code',
            'billing_country', 'tax_rate', 'discount_percent',
            'payment_terms', 'late_fee_percent', 'notes', 'internal_notes'
        ]
        widgets = {
            'invoice_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'INV-2024-001'
            }),
            'customer': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'order': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'billing_address_line1': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'billing_address_line2': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'billing_city': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'billing_state': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'billing_postal_code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'billing_country': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'placeholder': '8.25'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'payment_terms': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'late_fee_percent': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3
            }),
            'internal_notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3
            }),
        }


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0.01'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'customer', 'invoice', 'order', 'amount',
            'payment_date', 'payment_method', 'status', 'reference_number',
            'bank_name', 'notes'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'customer': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'invoice': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'order': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0.01'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Check number, transaction ID, etc.'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default status to completed
        if not self.instance.pk and not self.initial.get('status'):
            self.initial['status'] = 'completed'
        # Set default payment date to today
        if not self.instance.pk and not self.initial.get('payment_date'):
            from django.utils import timezone
            self.initial['payment_date'] = timezone.now().date()
        # Make optional fields
        self.fields['order'].required = False
        self.fields['customer'].required = False  # Customer is now optional for shop orders
        
        # Hide fields that are provided via initial data
        if self.initial.get('invoice'):
            self.fields['invoice'].widget = forms.HiddenInput()
        if self.initial.get('customer') is not None:  # Check for None specifically
            self.fields['customer'].widget = forms.HiddenInput()
        if self.initial.get('order') is not None:
            self.fields['order'].widget = forms.HiddenInput()
        else:
            # Always hide order if not provided
            self.fields['order'].widget = forms.HiddenInput()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Generate payment number if not set
        if not instance.payment_number:
            from django.utils import timezone
            today = timezone.now().strftime('%Y%m%d')
            # Get the count of payments created today
            count = Payment.objects.filter(
                payment_number__startswith=f'PAY-{today}'
            ).count() + 1
            instance.payment_number = f'PAY-{today}-{count:04d}'
        
        if commit:
            instance.save()
        return instance


class InvoiceShipmentForm(forms.ModelForm):
    class Meta:
        model = InvoiceShipment
        fields = [
            'supplier', 'carrier', 'tracking_number', 'tracking_url',
            'service_type', 'status', 'package_count', 'total_weight',
            'shipping_cost', 'insurance_amount', 'ship_date',
            'estimated_delivery', 'actual_delivery', 'delivered_to',
            'delivery_signature', 'delivery_notes', 'ship_to_name',
            'ship_to_company', 'ship_to_address_line1', 'ship_to_address_line2',
            'ship_to_city', 'ship_to_state', 'ship_to_postal_code',
            'ship_to_country', 'ship_to_phone', 'ship_to_email',
            'internal_notes'
        ]
        widgets = {
            'supplier': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'carrier': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'tracking_number': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter tracking number'
            }),
            'tracking_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://tracking.carrier.com/...'
            }),
            'service_type': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Ground, 2-Day Air'
            }),
            'status': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'package_count': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1'
            }),
            'total_weight': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'placeholder': 'Weight in pounds'
            }),
            'shipping_cost': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0'
            }),
            'insurance_amount': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0'
            }),
            'ship_date': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'estimated_delivery': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'actual_delivery': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'delivered_to': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Name of person who received'
            }),
            'delivery_signature': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Signature data or confirmation code'
            }),
            'delivery_notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Delivery instructions or notes'
            }),
            'ship_to_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'ship_to_company': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'ship_to_address_line1': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'ship_to_address_line2': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'ship_to_city': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'ship_to_state': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'ship_to_postal_code': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'ship_to_country': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'maxlength': '2'
            }),
            'ship_to_phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'ship_to_email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'internal_notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Internal notes about this shipment'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        invoice = kwargs.pop('invoice', None)
        super().__init__(*args, **kwargs)
        
        # Make shipping address fields optional since we auto-populate them
        shipping_fields = [
            'ship_to_name', 'ship_to_company', 'ship_to_address_line1', 
            'ship_to_address_line2', 'ship_to_city', 'ship_to_state', 
            'ship_to_postal_code', 'ship_to_country', 'ship_to_phone', 'ship_to_email'
        ]
        for field in shipping_fields:
            self.fields[field].required = False
        
        # If this is a new shipment and we have an invoice, pre-populate address
        if not self.instance.pk and invoice:
            if invoice.shipping_same_as_billing or not invoice.shipping_address_line1:
                # Use billing address
                self.initial['ship_to_name'] = f"{invoice.first_name} {invoice.last_name}".strip()
                self.initial['ship_to_company'] = invoice.customer.company if invoice.customer else ''
                self.initial['ship_to_address_line1'] = invoice.billing_address_line1
                self.initial['ship_to_address_line2'] = invoice.billing_address_line2
                self.initial['ship_to_city'] = invoice.billing_city
                self.initial['ship_to_state'] = invoice.billing_state
                self.initial['ship_to_postal_code'] = invoice.billing_postal_code
                self.initial['ship_to_country'] = invoice.billing_country or 'US'
            else:
                # Use shipping address
                self.initial['ship_to_name'] = f"{invoice.first_name} {invoice.last_name}".strip()
                self.initial['ship_to_company'] = invoice.customer.company if invoice.customer else ''
                self.initial['ship_to_address_line1'] = invoice.shipping_address_line1
                self.initial['ship_to_address_line2'] = invoice.shipping_address_line2
                self.initial['ship_to_city'] = invoice.shipping_city
                self.initial['ship_to_state'] = invoice.shipping_state
                self.initial['ship_to_postal_code'] = invoice.shipping_postal_code
                self.initial['ship_to_country'] = invoice.shipping_country or 'US'
            
            self.initial['ship_to_phone'] = invoice.phone
            self.initial['ship_to_email'] = invoice.email
            
        # Set default ship date to today
        if not self.instance.pk and not self.initial.get('ship_date'):
            from django.utils import timezone
            self.initial['ship_date'] = timezone.now()


class ShipmentItemForm(forms.ModelForm):
    class Meta:
        model = ShipmentItem
        fields = ['invoice_item', 'quantity_shipped', 'serial_numbers', 'notes']
        widgets = {
            'invoice_item': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'quantity_shipped': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0.01'
            }),
            'serial_numbers': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Enter serial numbers (JSON format)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Notes about this item'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        shipment = kwargs.pop('shipment', None)
        super().__init__(*args, **kwargs)
        
        # Filter invoice items to only show items from this shipment's invoice
        if shipment and shipment.invoice:
            self.fields['invoice_item'].queryset = shipment.invoice.items.all()


ShipmentItemFormSet = inlineformset_factory(
    InvoiceShipment, ShipmentItem,
    form=ShipmentItemForm,
    extra=1,
    can_delete=True,
    fields=['invoice_item', 'quantity_shipped', 'serial_numbers', 'notes']
)