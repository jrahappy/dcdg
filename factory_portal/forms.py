from django import forms
from factory.models import FactoryUser, WorkOrder, FulfillmentItem, Shipment


class FactoryProfileForm(forms.ModelForm):
    """Form for editing factory user profile"""
    class Meta:
        model = FactoryUser
        fields = ['employee_id', 'department', 'phone', 'mobile', 'notes']
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'department': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'mobile': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
        }


class WorkOrderUpdateForm(forms.ModelForm):
    """Form for updating work order status"""
    class Meta:
        model = WorkOrder
        fields = ['status', 'priority', 'expected_completion', 'internal_notes', 'production_notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'priority': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'expected_completion': forms.DateTimeInput(
                attrs={'class': 'input input-bordered w-full', 'type': 'datetime-local'}
            ),
            'internal_notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'production_notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
        }


class FulfillmentItemForm(forms.ModelForm):
    """Form for updating fulfillment item"""
    class Meta:
        model = FulfillmentItem
        fields = [
            'status', 'quantity_allocated', 'quantity_fulfilled',
            'warehouse_location', 'bin_location', 'notes', 'quality_check_notes'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'quantity_allocated': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'quantity_fulfilled': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'warehouse_location': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'bin_location': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'quality_check_notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
        }


class ShipmentForm(forms.ModelForm):
    """Form for creating shipment"""
    class Meta:
        model = Shipment
        fields = [
            'carrier', 'tracking_number', 'service_type',
            'ship_to_name', 'ship_to_company', 'ship_to_address_line1', 'ship_to_address_line2',
            'ship_to_city', 'ship_to_state', 'ship_to_postal_code', 'ship_to_country',
            'ship_to_phone', 'ship_to_email',
            'number_of_packages', 'total_weight', 'package_dimensions',
            'shipping_cost', 'insurance_cost',
            'ship_date', 'estimated_delivery',
            'special_instructions', 'internal_notes'
        ]
        widgets = {
            'carrier': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'tracking_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'service_type': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_company': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_address_line1': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_address_line2': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_city': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_state': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_postal_code': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_country': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_to_email': forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
            'number_of_packages': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'total_weight': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'package_dimensions': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'insurance_cost': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'ship_date': forms.DateTimeInput(attrs={'class': 'input input-bordered w-full', 'type': 'datetime-local'}),
            'estimated_delivery': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'special_instructions': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'internal_notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
        }