from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import PurchaseOrder, PurchaseOrderItem, Supplier, SupplierContact, SupplierPayment
from .forms import PurchaseOrderForm, PurchaseOrderItemFormSet, SupplierPaymentForm
from product.models import Product, Inventory
import json
from datetime import date
from decimal import Decimal


# Staff Required Mixin for all admin views
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to ensure user is staff"""
    def test_func(self):
        return self.request.user.is_staff


@staff_member_required
def purchase_order_list(request):
    """List all purchase orders with filters"""
    orders = PurchaseOrder.objects.select_related('created_by', 'supplier').prefetch_related('items__product').all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(reference_number__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        orders = orders.filter(order_date__gte=date_from)
    if date_to:
        orders = orders.filter(order_date__lte=date_to)
    
    # Filter by supplier
    supplier_filter = request.GET.get('supplier', '')
    if supplier_filter:
        orders = orders.filter(supplier_id=supplier_filter)
    
    # Order by date
    orders = orders.order_by('-order_date', '-created_at')
    
    # Get rows per page from request
    rows_per_page = request.GET.get('rows', '20')
    try:
        rows_per_page = int(rows_per_page)
    except (ValueError, TypeError):
        rows_per_page = 20
    
    # Pagination
    paginator = Paginator(orders, rows_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_orders = PurchaseOrder.objects.count()
    total_spent = PurchaseOrder.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    pending_count = PurchaseOrder.objects.filter(status__in=['draft', 'sent']).count()
    received_count = PurchaseOrder.objects.filter(status='received').count()
    overdue_count = PurchaseOrder.objects.filter(
        status__in=['sent', 'confirmed'],
        expected_delivery_date__lt=date.today()
    ).count()
    
    # Get suppliers for filter
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'supplier_filter': supplier_filter,
        'suppliers': suppliers,
        'date_from': date_from,
        'date_to': date_to,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'pending_count': pending_count,
        'received_count': received_count,
        'overdue_count': overdue_count,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
        'rows_per_page': rows_per_page,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'purchases/purchase_order_list_daisyui.html', context)


@staff_member_required
def purchase_order_detail(request, pk):
    """View purchase order details"""
    order = get_object_or_404(
        PurchaseOrder.objects.select_related('created_by', 'supplier').prefetch_related('items__product'),
        pk=pk
    )
    
    # Check which items can have inventory created
    total_pending_inventory = 0
    for item in order.items.all():
        item.can_create_inventory = (
            item.product.is_serial_number_managed and 
            item.quantity_received > 0 and
            order.status in ['partially_received', 'received']
        )
        # Count existing inventory items for this PO item
        item.inventory_created = Inventory.objects.filter(
            product=item.product,
            purchase_order_number=order.order_number
        ).count()
        
        # Calculate the difference for serial number managed items
        if item.product.is_serial_number_managed:
            item.inventory_difference = int(item.quantity) - item.inventory_created
            if item.inventory_difference > 0:
                total_pending_inventory += item.inventory_difference
        else:
            item.inventory_difference = 0
    
    # Calculate payment information
    total_paid = SupplierPayment.objects.filter(
        purchase_order=order,
        status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    balance_due = order.total_amount - total_paid
    
    # Get recent payments
    recent_payments = SupplierPayment.objects.filter(
        purchase_order=order
    ).order_by('-date', '-id')[:5]
    
    context = {
        'order': order,
        'total_pending_inventory': total_pending_inventory,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'purchases/purchase_order_detail_daisyui.html', context)


@staff_member_required
def purchase_order_create(request):
    """Create new purchase order"""
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.created_by = request.user
                order.save()
                
                # Save the formset
                formset.instance = order
                formset.save()
                
                # Calculate totals
                order.calculate_totals()
                
                messages.success(request, f'Purchase Order "{order.order_number}" has been created successfully.')
                return redirect('purchases:purchase_order_detail', pk=order.pk)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet(prefix='items')
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Purchase Order',
        'button_text': 'Create Order'
    }
    
    return render(request, 'purchases/purchase_order_form.html', context)


@staff_member_required
def purchase_order_update(request, pk):
    """Update purchase order"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=order)
        formset = PurchaseOrderItemFormSet(request.POST, instance=order, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save()
                formset.save()
                
                # Calculate totals
                order.calculate_totals()
                
                messages.success(request, f'Purchase Order "{order.order_number}" has been updated successfully.')
                return redirect('purchases:purchase_order_detail', pk=order.pk)
    else:
        form = PurchaseOrderForm(instance=order)
        formset = PurchaseOrderItemFormSet(instance=order, prefix='items')
    
    context = {
        'form': form,
        'formset': formset,
        'order': order,
        'title': f'Edit Purchase Order: {order.order_number}',
        'button_text': 'Update Order'
    }
    
    return render(request, 'purchases/purchase_order_form.html', context)


@staff_member_required
def purchase_order_delete(request, pk):
    """Delete purchase order"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if request.method == 'POST':
        order_number = order.order_number
        order.delete()
        messages.success(request, f'Purchase Order "{order_number}" has been deleted successfully.')
        return redirect('purchases:purchase_order_list')
    
    context = {
        'order': order,
    }
    
    return render(request, 'purchases/purchase_order_confirm_delete.html', context)


@staff_member_required
def purchase_order_receive(request, pk):
    """Receive items for a purchase order"""
    order = get_object_or_404(
        PurchaseOrder.objects.prefetch_related('items__product'),
        pk=pk
    )
    
    if request.method == 'POST':
        # Process received quantities
        with transaction.atomic():
            for item in order.items.all():
                received_qty = request.POST.get(f'received_{item.id}', '0')
                try:
                    received_qty = float(received_qty)
                    if received_qty > 0:
                        item.quantity_received = min(
                            item.quantity_received + received_qty,
                            item.quantity
                        )
                        item.save()
                except ValueError:
                    pass
            
            # Update order status
            order.update_receive_status()
            
            # Set received date if fully received
            if order.status == 'received' and not order.received_date:
                order.received_date = date.today()
                order.save()
            
            messages.success(request, 'Items received successfully.')
            return redirect('purchases:purchase_order_detail', pk=order.pk)
    
    context = {
        'order': order,
    }
    
    return render(request, 'purchases/purchase_order_receive.html', context)


@staff_member_required
def supplier_payment_create(request, pk):
    """Create a payment for a purchase order"""
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    # Calculate total paid so far
    total_paid = SupplierPayment.objects.filter(
        purchase_order=purchase_order,
        status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    balance_due = purchase_order.total_amount - total_paid
    
    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST, purchase_order=purchase_order)
        if form.is_valid():
            # The form's save method handles company assignment now
            payment = form.save(commit=False)
            
            # Ensure we have required fields
            payment.purchase_order = purchase_order
            payment.supplier = purchase_order.supplier
            
            # Set bank account code (default to cash account)
            payment.bank_account_code = "1010"  # Bank - Checking
            
            # Double-check company is set
            if not payment.company:
                from customer.models import Organization
                payment.company = Organization.objects.first() or Organization.objects.create(
                    name="Default Company",
                    code="DEFAULT"
                )
            
            # Save the payment
            payment.save()
            
            # Post to accounting ledger
            try:
                from accounting.services import post_outgoing_payment
                
                # Post the payment to ledger
                journal_entry = post_outgoing_payment(payment)
                
                messages.success(
                    request,
                    f"Payment of ${payment.amount} recorded successfully and posted to ledger (Journal Entry #{journal_entry.pk})"
                )
            except Exception as e:
                messages.warning(
                    request,
                    f"Payment recorded but could not post to ledger: {str(e)}"
                )
            
            # Update purchase order payment status
            new_total_paid = total_paid + payment.amount
            if new_total_paid >= purchase_order.total_amount:
                # Fully paid
                if purchase_order.status == 'received':
                    purchase_order.status = 'received'  # Keep as received if already received
                messages.info(request, "Purchase order is now fully paid!")
            
            return redirect('purchases:purchase_order_detail', pk=purchase_order.pk)
    else:
        form = SupplierPaymentForm(purchase_order=purchase_order)
    
    # Get payment history
    payments = SupplierPayment.objects.filter(
        purchase_order=purchase_order
    ).order_by('-date', '-id')
    
    context = {
        'order': purchase_order,
        'form': form,
        'balance_due': balance_due,
        'total_paid': total_paid,
        'payments': payments,
    }
    
    return render(request, 'purchases/supplier_payment_form.html', context)


@staff_member_required
@require_POST
def create_inventory_items(request, pk, item_id):
    """Create inventory items for a purchase order item"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, pk=item_id, purchase_order=order)
    
    # Check if product is serial number managed
    if not item.product.is_serial_number_managed:
        return JsonResponse({
            'success': False,
            'error': 'This product is not serial number managed.'
        }, status=400)
    
    # For serial number managed items, we allow inventory creation even before receiving
    # This allows pre-registration of serial numbers
    
    # Get serial numbers from request
    data = json.loads(request.body)
    serial_numbers = data.get('serial_numbers', '')
    
    # Split and clean serial numbers
    serial_list = [sn.strip() for sn in serial_numbers.split(',') if sn.strip()]
    
    if not serial_list:
        return JsonResponse({
            'success': False,
            'error': 'Please provide at least one serial number.'
        }, status=400)
    
    # Check for duplicates within the submitted list
    seen = set()
    duplicates_in_list = set()
    for sn in serial_list:
        if sn in seen:
            duplicates_in_list.add(sn)
        seen.add(sn)
    
    if duplicates_in_list:
        return JsonResponse({
            'success': False,
            'error': f'Duplicate serial numbers in your list: {", ".join(sorted(duplicates_in_list))}'
        }, status=400)
    
    # Check for existing serial numbers in database
    existing_serials = list(Inventory.objects.filter(
        serial_number__in=serial_list
    ).values_list('serial_number', flat=True))
    
    if existing_serials:
        return JsonResponse({
            'success': False,
            'error': f'The following serial numbers already exist in the system: {", ".join(sorted(existing_serials))}'
        }, status=400)
    
    # Create inventory items
    created_items = []
    with transaction.atomic():
        for serial_number in serial_list:
            inventory = Inventory.objects.create(
                product=item.product,
                serial_number=serial_number,
                status='available',
                condition='New',
                purchase_date=order.order_date,
                purchase_price=item.unit_cost,
                supplier=order.supplier.name if order.supplier else '',
                purchase_order_number=order.order_number,
                warranty_start_date=order.received_date or date.today(),
                current_location='Warehouse',
                created_by=request.user
            )
            
            # Calculate warranty end date (default 12 months)
            # TODO: Uncomment when python-dateutil is installed
            # inventory.calculate_warranty_end_date(12)
            # inventory.update_warranty_status()
            
            created_items.append(inventory.serial_number)
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully created {len(created_items)} inventory items with serial numbers: {", ".join(created_items[:3])}{"..." if len(created_items) > 3 else ""}',
        'created_items': created_items,
        'count': len(created_items)
    })


@staff_member_required
def get_product_info(request, product_id):
    """Get product information for AJAX requests"""
    try:
        product = Product.objects.get(pk=product_id)
        return JsonResponse({
            'success': True,
            'product': {
                'name': product.name,
                'description': product.short_description,
                'cost': str(product.cost) if product.cost else '0',
                'is_serial_number_managed': product.is_serial_number_managed
            }
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found.'
        }, status=404)


# Supplier Views
@staff_member_required
def supplier_list(request):
    """List all suppliers"""
    suppliers = Supplier.objects.select_related('created_by').all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Filter by active status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        suppliers = suppliers.filter(is_active=True)
    elif status_filter == 'inactive':
        suppliers = suppliers.filter(is_active=False)
    
    # Filter by location
    location_filter = request.GET.get('location', '')
    if location_filter:
        suppliers = suppliers.filter(city=location_filter)
    
    # Order by name
    suppliers = suppliers.order_by('name')
    
    # Pagination
    paginator = Paginator(suppliers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_suppliers = Supplier.objects.count()
    active_count = Supplier.objects.filter(is_active=True).count()
    total_orders = PurchaseOrder.objects.count()
    total_spent = PurchaseOrder.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Get unique locations for filter
    locations = Supplier.objects.exclude(
        city__isnull=True
    ).exclude(
        city=''
    ).values_list('city', flat=True).distinct().order_by('city')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'location_filter': location_filter,
        'locations': locations,
        'total_suppliers': total_suppliers,
        'active_count': active_count,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'purchases/supplier_list_daisyui.html', context)


@staff_member_required
def supplier_detail(request, pk):
    """View supplier details"""
    supplier = get_object_or_404(
        Supplier.objects.prefetch_related('purchase_orders', 'contacts', 'documents'),
        pk=pk
    )
    
    # Get recent purchase orders
    recent_orders = supplier.purchase_orders.order_by('-order_date')[:10]
    
    # Calculate statistics
    total_purchase_value = supplier.purchase_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    pending_orders_count = supplier.purchase_orders.exclude(
        status__in=['received', 'cancelled']
    ).count()
    
    context = {
        'supplier': supplier,
        'recent_orders': recent_orders,
        'total_purchase_value': total_purchase_value,
        'pending_orders_count': pending_orders_count,
    }
    
    return render(request, 'purchases/supplier_detail_daisyui.html', context)


@staff_member_required
def supplier_create(request):
    """Create new supplier"""
    if request.method == 'POST':
        # Create supplier
        supplier = Supplier(
            name=request.POST.get('name'),
            contact_person=request.POST.get('contact_person', ''),
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
            address_line1=request.POST.get('address_line1', ''),
            address_line2=request.POST.get('address_line2', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            postal_code=request.POST.get('postal_code', ''),
            country=request.POST.get('country', 'USA'),
            internal_notes=request.POST.get('internal_notes', ''),
            is_active=request.POST.get('is_active', 'on') == 'on',
            created_by=request.user
        )
        
        try:
            supplier.full_clean()
            supplier.save()
            messages.success(request, f'Supplier "{supplier.name}" has been created successfully.')
            return redirect('purchases:supplier_detail', pk=supplier.pk)
        except Exception as e:
            messages.error(request, f'Error creating supplier: {str(e)}')
    
    return render(request, 'purchases/supplier_form_daisyui.html', {
        'title': 'Create Supplier',
        'button_text': 'Create Supplier'
    })


@staff_member_required
def supplier_update(request, pk):
    """Update supplier"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.name = request.POST.get('name', supplier.name)
        supplier.contact_person = request.POST.get('contact_person', '')
        supplier.email = request.POST.get('email', '')
        supplier.phone = request.POST.get('phone', '')
        supplier.address_line1 = request.POST.get('address_line1', '')
        supplier.address_line2 = request.POST.get('address_line2', '')
        supplier.city = request.POST.get('city', '')
        supplier.state = request.POST.get('state', '')
        supplier.postal_code = request.POST.get('postal_code', '')
        supplier.country = request.POST.get('country', 'USA')
        supplier.internal_notes = request.POST.get('internal_notes', '')
        supplier.is_active = request.POST.get('is_active', 'on') == 'on'
        
        try:
            supplier.full_clean()
            supplier.save()
            messages.success(request, f'Supplier "{supplier.name}" has been updated successfully.')
            return redirect('purchases:supplier_detail', pk=supplier.pk)
        except Exception as e:
            messages.error(request, f'Error updating supplier: {str(e)}')
    
    return render(request, 'purchases/supplier_form_daisyui.html', {
        'supplier': supplier,
        'title': f'Edit Supplier: {supplier.name}',
        'button_text': 'Update Supplier'
    })


@staff_member_required
def supplier_delete(request, pk):
    """Delete supplier"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # Check if supplier has purchase orders
    if supplier.purchase_orders.exists():
        messages.error(request, 'Cannot delete supplier with existing purchase orders.')
        return redirect('purchases:supplier_detail', pk=pk)
    
    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f'Supplier "{supplier_name}" has been deleted successfully.')
        return redirect('purchases:supplier_list')
    
    context = {
        'supplier': supplier,
    }
    
    return render(request, 'purchases/supplier_confirm_delete.html', context)


# Supplier Contact Views
@staff_member_required
@require_POST
def supplier_contact_add(request, supplier_pk):
    """Add a contact to a supplier via AJAX"""
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    
    try:
        data = json.loads(request.body)
        
        contact = SupplierContact.objects.create(
            supplier=supplier,
            name=data.get('name', ''),
            position=data.get('position', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            notes=data.get('notes', ''),
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'contact': {
                'id': contact.id,
                'name': contact.name,
                'position': contact.position,
                'email': contact.email,
                'phone': contact.phone,
                'notes': contact.notes
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@staff_member_required
@require_POST
def supplier_contact_delete(request, supplier_pk, contact_pk):
    """Delete a supplier contact via AJAX"""
    supplier = get_object_or_404(Supplier, pk=supplier_pk)
    contact = get_object_or_404(SupplierContact, pk=contact_pk, supplier=supplier)
    
    contact.delete()
    
    return JsonResponse({'success': True})


# Multi-step Purchase Order Creation Views
class PurchaseOrderCreateStep1View(StaffRequiredMixin, TemplateView):
    template_name = 'purchases/purchase_order_create_step1_daisyui.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['suppliers'] = Supplier.objects.filter(is_active=True).order_by('name')
        return context
    
    def post(self, request, *args, **kwargs):
        supplier_id = request.POST.get('supplier_id')
        order_date = request.POST.get('order_date')
        expected_delivery_date = request.POST.get('expected_delivery_date')
        
        if supplier_id:
            # Store in session
            request.session['po_supplier_id'] = supplier_id
            request.session['po_order_date'] = order_date
            request.session['po_expected_delivery_date'] = expected_delivery_date
            return redirect('purchases:purchase_order_create_step2')
        else:
            messages.error(request, 'Please select a supplier')
            return redirect('purchases:purchase_order_create_step1')


class PurchaseOrderCreateStep2View(StaffRequiredMixin, TemplateView):
    template_name = 'purchases/purchase_order_create_step2_daisyui.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if supplier is selected
        if 'po_supplier_id' not in request.session:
            messages.warning(request, 'Please select a supplier first')
            return redirect('purchases:purchase_order_create_step1')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier_id = self.request.session.get('po_supplier_id')
        context['supplier'] = get_object_or_404(Supplier, pk=supplier_id)
        context['products'] = Product.objects.filter(status='active').order_by('name')
        
        # Get items from session
        po_items = self.request.session.get('po_items', [])
        context['po_items'] = po_items
        
        # Calculate totals
        subtotal = sum(Decimal(str(item['line_total'])) for item in po_items)
        context['subtotal'] = subtotal
        
        return context
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'add_item':
            # Add item to purchase order
            product_id = request.POST.get('product_id')
            if product_id:
                product = get_object_or_404(Product, pk=product_id)
                quantity = int(request.POST.get('quantity', 1))
                unit_cost = Decimal(request.POST.get('unit_cost', product.cost or 0))
                
                # Get current items from session
                po_items = request.session.get('po_items', [])
                
                # Check if product already exists
                existing_item = None
                for item in po_items:
                    if item['product_id'] == int(product_id):
                        existing_item = item
                        break
                
                if existing_item:
                    # Update quantity
                    existing_quantity = Decimal(str(existing_item['quantity']))
                    new_quantity = existing_quantity + quantity
                    existing_item['quantity'] = str(new_quantity)
                    existing_item['line_total'] = str(new_quantity * Decimal(str(existing_item['unit_cost'])))
                else:
                    # Add new item
                    new_item = {
                        'product_id': product.id,
                        'product_name': product.name,
                        'product_sku': product.sku,
                        'description': request.POST.get('description', product.short_description or ''),
                        'quantity': str(quantity),
                        'unit_cost': str(unit_cost),
                        'line_total': str(quantity * unit_cost)
                    }
                    po_items.append(new_item)
                
                request.session['po_items'] = po_items
                messages.success(request, f'Added {product.name} to purchase order')
            
            return redirect('purchases:purchase_order_create_step2')
        
        elif action == 'remove_item':
            # Remove item from purchase order
            product_id = request.POST.get('product_id')
            if product_id:
                po_items = request.session.get('po_items', [])
                po_items = [item for item in po_items if item['product_id'] != int(product_id)]
                request.session['po_items'] = po_items
                messages.success(request, 'Item removed from purchase order')
            
            return redirect('purchases:purchase_order_create_step2')
        
        elif action == 'next':
            # Go to step 3
            po_items = request.session.get('po_items', [])
            if not po_items:
                messages.warning(request, 'Please add items to the purchase order')
                return redirect('purchases:purchase_order_create_step2')
            
            # Store additional details
            request.session['po_tax_rate'] = request.POST.get('tax_rate', '0')
            request.session['po_shipping_cost'] = request.POST.get('shipping_cost', '0')
            request.session['po_discount_percent'] = request.POST.get('discount_percent', '0')
            request.session['po_notes'] = request.POST.get('notes', '')
            request.session['po_internal_notes'] = request.POST.get('internal_notes', '')
            
            return redirect('purchases:purchase_order_create_step3')
        
        return redirect('purchases:purchase_order_create_step2')


class PurchaseOrderCreateStep3View(StaffRequiredMixin, TemplateView):
    template_name = 'purchases/purchase_order_create_step3.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if supplier and items are in session
        if 'po_supplier_id' not in request.session:
            messages.warning(request, 'Please select a supplier first')
            return redirect('purchases:purchase_order_create_step1')
        
        po_items = request.session.get('po_items', [])
        if not po_items:
            messages.warning(request, 'Please add items to the purchase order')
            return redirect('purchases:purchase_order_create_step2')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get supplier
        supplier_id = self.request.session.get('po_supplier_id')
        supplier = get_object_or_404(Supplier, pk=supplier_id)
        context['supplier'] = supplier
        
        # Get dates
        context['order_date'] = self.request.session.get('po_order_date')
        context['expected_delivery_date'] = self.request.session.get('po_expected_delivery_date')
        
        # Get items
        po_items = self.request.session.get('po_items', [])
        context['po_items'] = po_items
        
        # Get additional details with proper validation
        tax_rate_str = self.request.session.get('po_tax_rate', '0')
        shipping_cost_str = self.request.session.get('po_shipping_cost', '0')
        discount_percent_str = self.request.session.get('po_discount_percent', '0')
        
        # Convert to Decimal with validation
        try:
            tax_rate = Decimal(str(tax_rate_str) if tax_rate_str else '0')
        except:
            tax_rate = Decimal('0')
            
        try:
            shipping_cost = Decimal(str(shipping_cost_str) if shipping_cost_str else '0')
        except:
            shipping_cost = Decimal('0')
            
        try:
            discount_percent = Decimal(str(discount_percent_str) if discount_percent_str else '0')
        except:
            discount_percent = Decimal('0')
        
        context['tax_rate'] = tax_rate
        context['shipping_cost'] = shipping_cost
        context['discount_percent'] = discount_percent
        context['notes'] = self.request.session.get('po_notes', '')
        context['internal_notes'] = self.request.session.get('po_internal_notes', '')
        
        # Calculate totals with proper validation
        subtotal = Decimal('0')
        for item in po_items:
            try:
                subtotal += Decimal(str(item.get('line_total', '0')))
            except:
                # Skip invalid line totals
                pass
        discount_amount = subtotal * (discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        tax_amount = subtotal_after_discount * (tax_rate / 100)
        total = subtotal_after_discount + tax_amount + shipping_cost
        
        context['subtotal'] = subtotal
        context['discount_amount'] = discount_amount
        context['tax_amount'] = tax_amount
        context['total'] = total
        
        return context
    
    def post(self, request, *args, **kwargs):
        # Create the purchase order
        with transaction.atomic():
            # Get data from session
            supplier_id = request.session.get('po_supplier_id')
            supplier = get_object_or_404(Supplier, pk=supplier_id)
            
            # Generate order number
            last_order = PurchaseOrder.objects.order_by('-id').first()
            if last_order:
                order_number = f"PO-{last_order.id + 1:05d}"
            else:
                order_number = "PO-00001"
            
            # Create purchase order
            order_date_str = request.session.get('po_order_date')
            if order_date_str:
                try:
                    order_date = date.fromisoformat(order_date_str)
                except (ValueError, TypeError):
                    order_date = date.today()
            else:
                order_date = date.today()
            
            expected_delivery_date_str = request.session.get('po_expected_delivery_date')
            expected_delivery_date = None
            if expected_delivery_date_str:
                try:
                    expected_delivery_date = date.fromisoformat(expected_delivery_date_str)
                except (ValueError, TypeError):
                    expected_delivery_date = None
            
            # Convert session values to Decimal with validation
            try:
                tax_rate = Decimal(str(request.session.get('po_tax_rate', '0') or '0'))
            except:
                tax_rate = Decimal('0')
                
            try:
                shipping_cost = Decimal(str(request.session.get('po_shipping_cost', '0') or '0'))
            except:
                shipping_cost = Decimal('0')
                
            try:
                discount_percent = Decimal(str(request.session.get('po_discount_percent', '0') or '0'))
            except:
                discount_percent = Decimal('0')
            
            order = PurchaseOrder.objects.create(
                order_number=order_number,
                supplier=supplier,
                order_date=order_date,
                expected_delivery_date=expected_delivery_date,
                tax_rate=tax_rate,
                shipping_cost=shipping_cost,
                discount_percent=discount_percent,
                notes=request.session.get('po_notes', ''),
                internal_notes=request.session.get('po_internal_notes', ''),
                status='draft',
                created_by=request.user
            )
            
            # Create order items
            po_items = request.session.get('po_items', [])
            for item in po_items:
                product = Product.objects.get(pk=item['product_id'])
                PurchaseOrderItem.objects.create(
                    purchase_order=order,
                    product=product,
                    description=item['description'],
                    quantity=Decimal(str(item['quantity'])),
                    unit_cost=Decimal(str(item['unit_cost'])),
                    quantity_received=0
                )
            
            # Calculate totals
            order.calculate_totals()
            
            # Clear session data
            for key in ['po_supplier_id', 'po_order_date', 'po_expected_delivery_date', 
                       'po_items', 'po_tax_rate', 'po_shipping_cost', 'po_discount_percent',
                       'po_notes', 'po_internal_notes']:
                request.session.pop(key, None)
            
            messages.success(request, f'Purchase Order "{order.order_number}" has been created successfully.')
            return redirect('purchases:purchase_order_detail', pk=order.pk)


# Multi-step Purchase Order Edit Views
class PurchaseOrderEditStep1View(StaffRequiredMixin, TemplateView):
    template_name = 'purchases/purchase_order_edit_step1_daisyui.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(PurchaseOrder, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.order
        context['suppliers'] = Supplier.objects.filter(is_active=True).order_by('name')
        return context
    
    def post(self, request, *args, **kwargs):
        supplier_id = request.POST.get('supplier_id')
        order_date = request.POST.get('order_date')
        expected_delivery_date = request.POST.get('expected_delivery_date')
        
        if supplier_id:
            # Store in session
            request.session['po_edit_id'] = self.order.id
            request.session['po_edit_supplier_id'] = supplier_id
            request.session['po_edit_order_date'] = order_date
            request.session['po_edit_expected_delivery_date'] = expected_delivery_date
            
            # Store existing items in session
            po_items = []
            for item in self.order.items.all():
                po_items.append({
                    'product_id': item.product.id,
                    'product_name': item.product.name,
                    'product_sku': item.product.sku,
                    'description': item.description,
                    'quantity': str(item.quantity),
                    'unit_cost': str(item.unit_cost),
                    'line_total': str(item.line_total)
                })
            request.session['po_edit_items'] = po_items
            
            return redirect('purchases:purchase_order_edit_step2', pk=self.order.pk)
        else:
            messages.error(request, 'Please select a supplier')
            return redirect('purchases:purchase_order_edit_step1', pk=self.order.pk)


class PurchaseOrderEditStep2View(StaffRequiredMixin, TemplateView):
    template_name = 'purchases/purchase_order_edit_step2_daisyui.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if order is being edited
        if 'po_edit_id' not in request.session:
            messages.warning(request, 'Please start from the beginning')
            return redirect('purchases:purchase_order_edit_step1', pk=kwargs['pk'])
        
        self.order = get_object_or_404(PurchaseOrder, pk=kwargs['pk'])
        if self.order.id != request.session.get('po_edit_id'):
            messages.warning(request, 'Session mismatch. Please start again.')
            return redirect('purchases:purchase_order_edit_step1', pk=kwargs['pk'])
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.order
        supplier_id = self.request.session.get('po_edit_supplier_id')
        context['supplier'] = get_object_or_404(Supplier, pk=supplier_id)
        context['products'] = Product.objects.filter(status='active').order_by('name')
        
        # Get items from session
        po_items = self.request.session.get('po_edit_items', [])
        context['po_items'] = po_items
        
        # Calculate totals
        subtotal = sum(Decimal(str(item['line_total'])) for item in po_items)
        context['subtotal'] = subtotal
        
        # Get existing values
        context['tax_rate'] = float(self.order.tax_rate)
        context['shipping_cost'] = float(self.order.shipping_cost)
        context['discount_percent'] = float(self.order.discount_percent)
        context['notes'] = self.order.notes
        context['internal_notes'] = self.order.internal_notes
        
        return context
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'add_item':
            # Add item to purchase order
            product_id = request.POST.get('product_id')
            if product_id:
                product = get_object_or_404(Product, pk=product_id)
                quantity = int(request.POST.get('quantity', 1))
                unit_cost = Decimal(request.POST.get('unit_cost', product.cost or 0))
                
                # Get current items from session
                po_items = request.session.get('po_edit_items', [])
                
                # Check if product already exists
                existing_item = None
                for item in po_items:
                    if item['product_id'] == int(product_id):
                        existing_item = item
                        break
                
                if existing_item:
                    # Update quantity
                    existing_quantity = Decimal(str(existing_item['quantity']))
                    new_quantity = existing_quantity + quantity
                    existing_item['quantity'] = str(new_quantity)
                    existing_item['line_total'] = str(new_quantity * Decimal(str(existing_item['unit_cost'])))
                else:
                    # Add new item
                    new_item = {
                        'product_id': product.id,
                        'product_name': product.name,
                        'product_sku': product.sku,
                        'description': request.POST.get('description', product.short_description or ''),
                        'quantity': str(quantity),
                        'unit_cost': str(unit_cost),
                        'line_total': str(quantity * unit_cost)
                    }
                    po_items.append(new_item)
                
                request.session['po_edit_items'] = po_items
                messages.success(request, f'Added {product.name} to purchase order')
            
            return redirect('purchases:purchase_order_edit_step2', pk=self.order.pk)
        
        elif action == 'remove_item':
            # Remove item from purchase order
            product_id = request.POST.get('product_id')
            if product_id:
                po_items = request.session.get('po_edit_items', [])
                po_items = [item for item in po_items if item['product_id'] != int(product_id)]
                request.session['po_edit_items'] = po_items
                messages.success(request, 'Item removed from purchase order')
            
            return redirect('purchases:purchase_order_edit_step2', pk=self.order.pk)
        
        elif action == 'next':
            # Go to step 3
            po_items = request.session.get('po_edit_items', [])
            if not po_items:
                messages.warning(request, 'Please add items to the purchase order')
                return redirect('purchases:purchase_order_edit_step2', pk=self.order.pk)
            
            # Store additional details
            request.session['po_edit_tax_rate'] = request.POST.get('tax_rate', '0')
            request.session['po_edit_shipping_cost'] = request.POST.get('shipping_cost', '0')
            request.session['po_edit_discount_percent'] = request.POST.get('discount_percent', '0')
            request.session['po_edit_notes'] = request.POST.get('notes', '')
            request.session['po_edit_internal_notes'] = request.POST.get('internal_notes', '')
            
            return redirect('purchases:purchase_order_edit_step3', pk=self.order.pk)
        
        return redirect('purchases:purchase_order_edit_step2', pk=self.order.pk)


class PurchaseOrderEditStep3View(StaffRequiredMixin, TemplateView):
    template_name = 'purchases/purchase_order_edit_step3_daisyui.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if order is being edited
        if 'po_edit_id' not in request.session:
            messages.warning(request, 'Please start from the beginning')
            return redirect('purchases:purchase_order_edit_step1', pk=kwargs['pk'])
        
        self.order = get_object_or_404(PurchaseOrder, pk=kwargs['pk'])
        if self.order.id != request.session.get('po_edit_id'):
            messages.warning(request, 'Session mismatch. Please start again.')
            return redirect('purchases:purchase_order_edit_step1', pk=kwargs['pk'])
        
        po_items = request.session.get('po_edit_items', [])
        if not po_items:
            messages.warning(request, 'Please add items to the purchase order')
            return redirect('purchases:purchase_order_edit_step2', pk=self.order.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.order
        
        # Get supplier
        supplier_id = self.request.session.get('po_edit_supplier_id')
        supplier = get_object_or_404(Supplier, pk=supplier_id)
        context['supplier'] = supplier
        
        # Get dates
        context['order_date'] = self.request.session.get('po_edit_order_date')
        context['expected_delivery_date'] = self.request.session.get('po_edit_expected_delivery_date')
        
        # Get items
        po_items = self.request.session.get('po_edit_items', [])
        context['po_items'] = po_items
        
        # Get additional details with proper validation
        tax_rate_str = self.request.session.get('po_edit_tax_rate', '0')
        shipping_cost_str = self.request.session.get('po_edit_shipping_cost', '0')
        discount_percent_str = self.request.session.get('po_edit_discount_percent', '0')
        
        # Convert to Decimal with validation
        try:
            tax_rate = Decimal(str(tax_rate_str) if tax_rate_str else '0')
        except:
            tax_rate = Decimal('0')
            
        try:
            shipping_cost = Decimal(str(shipping_cost_str) if shipping_cost_str else '0')
        except:
            shipping_cost = Decimal('0')
            
        try:
            discount_percent = Decimal(str(discount_percent_str) if discount_percent_str else '0')
        except:
            discount_percent = Decimal('0')
        
        context['tax_rate'] = tax_rate
        context['shipping_cost'] = shipping_cost
        context['discount_percent'] = discount_percent
        context['notes'] = self.request.session.get('po_edit_notes', '')
        context['internal_notes'] = self.request.session.get('po_edit_internal_notes', '')
        
        # Calculate totals with proper validation
        subtotal = Decimal('0')
        for item in po_items:
            try:
                subtotal += Decimal(str(item.get('line_total', '0')))
            except:
                # Skip invalid line totals
                pass
        discount_amount = subtotal * (discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        tax_amount = subtotal_after_discount * (tax_rate / 100)
        total = subtotal_after_discount + tax_amount + shipping_cost
        
        context['subtotal'] = subtotal
        context['discount_amount'] = discount_amount
        context['tax_amount'] = tax_amount
        context['total'] = total
        
        return context
    
    def post(self, request, *args, **kwargs):
        # Update the purchase order
        with transaction.atomic():
            # Get data from session
            supplier_id = request.session.get('po_edit_supplier_id')
            supplier = get_object_or_404(Supplier, pk=supplier_id)
            
            # Parse dates
            order_date_str = request.session.get('po_edit_order_date')
            if order_date_str:
                try:
                    order_date = date.fromisoformat(order_date_str)
                except (ValueError, TypeError):
                    order_date = self.order.order_date
            else:
                order_date = self.order.order_date
            
            expected_delivery_date_str = request.session.get('po_edit_expected_delivery_date')
            expected_delivery_date = None
            if expected_delivery_date_str:
                try:
                    expected_delivery_date = date.fromisoformat(expected_delivery_date_str)
                except (ValueError, TypeError):
                    expected_delivery_date = None
            
            # Update purchase order
            self.order.supplier = supplier
            self.order.order_date = order_date
            self.order.expected_delivery_date = expected_delivery_date
            # Convert session values to Decimal with validation
            try:
                self.order.tax_rate = Decimal(str(request.session.get('po_edit_tax_rate', '0') or '0'))
            except:
                self.order.tax_rate = Decimal('0')
                
            try:
                self.order.shipping_cost = Decimal(str(request.session.get('po_edit_shipping_cost', '0') or '0'))
            except:
                self.order.shipping_cost = Decimal('0')
                
            try:
                self.order.discount_percent = Decimal(str(request.session.get('po_edit_discount_percent', '0') or '0'))
            except:
                self.order.discount_percent = Decimal('0')
            self.order.notes = request.session.get('po_edit_notes', '')
            self.order.internal_notes = request.session.get('po_edit_internal_notes', '')
            self.order.save()
            
            # Delete existing items
            self.order.items.all().delete()
            
            # Create new order items
            po_items = request.session.get('po_edit_items', [])
            for item in po_items:
                product = Product.objects.get(pk=item['product_id'])
                PurchaseOrderItem.objects.create(
                    purchase_order=self.order,
                    product=product,
                    description=item['description'],
                    quantity=item['quantity'],
                    unit_cost=Decimal(str(item['unit_cost'])),
                    quantity_received=0
                )
            
            # Calculate totals
            self.order.calculate_totals()
            
            # Clear session data
            for key in ['po_edit_id', 'po_edit_supplier_id', 'po_edit_order_date', 
                       'po_edit_expected_delivery_date', 'po_edit_items', 'po_edit_tax_rate', 
                       'po_edit_shipping_cost', 'po_edit_discount_percent',
                       'po_edit_notes', 'po_edit_internal_notes']:
                request.session.pop(key, None)
            
            messages.success(request, f'Purchase Order "{self.order.order_number}" has been updated successfully.')
            return redirect('purchases:purchase_order_detail', pk=self.order.pk)


@staff_member_required
def purchase_order_inventory_list(request, pk):
    """HTMX view to show inventory items for a purchase order inline"""
    order = get_object_or_404(PurchaseOrder, pk=pk)
    
    # Get all inventory items for this purchase order
    inventory_items = Inventory.objects.filter(
        purchase_order_number=order.order_number
    ).select_related('product', 'customer', 'assigned_to').order_by('product__name', 'serial_number')
    
    # Group inventory by product for better display
    inventory_by_product = {}
    for item in inventory_items:
        if item.product.id not in inventory_by_product:
            inventory_by_product[item.product.id] = {
                'product': item.product,
                'items': []
            }
        inventory_by_product[item.product.id]['items'].append(item)
    
    context = {
        'order': order,
        'inventory_by_product': inventory_by_product,
        'total_inventory': inventory_items.count()
    }
    
    return render(request, 'purchases/partials/inventory_list.html', context)