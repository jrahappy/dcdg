from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.urls import reverse

from factory.models import FactoryUser, WorkOrder, FulfillmentItem, Shipment, SupplyRequest
from sales.models import Invoice, InvoiceItem
from purchases.models import Supplier, PurchaseOrder, PurchaseOrderItem
from .forms import FactoryProfileForm, WorkOrderUpdateForm, FulfillmentItemForm, ShipmentForm
from decimal import Decimal
from datetime import datetime, timedelta


def factory_user_required(view_func):
    """Decorator to ensure user has factory profile"""
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')
        
        # Check if user has factory profile
        try:
            factory_user = request.user.factory_profile
            if not factory_user.is_active:
                return HttpResponseForbidden("Your factory account is inactive.")
        except FactoryUser.DoesNotExist:
            return HttpResponseForbidden("You don't have factory access.")
        
        return view_func(request, *args, **kwargs)
    return wrapped_view


@factory_user_required
def dashboard(request):
    """Factory dashboard overview"""
    factory_user = request.user.factory_profile
    
    # Get customer orders (invoices) that have items from this supplier
    from django.db.models import Exists, OuterRef
    from sales.models import InvoiceItem
    
    # Subquery to check if invoice has items from this supplier
    has_supplier_items = InvoiceItem.objects.filter(
        invoice=OuterRef('pk'),
        product__supplier=factory_user.supplier
    )
    
    # Get invoices with items from this supplier
    customer_orders = Invoice.objects.filter(
        Exists(has_supplier_items)
    )
    
    # Statistics based on shipping status
    from django.db.models import Q
    stats = {
        'total_orders': customer_orders.count(),
        'pending_orders': customer_orders.filter(Q(shipping_status='pending') | Q(shipping_status__isnull=True)).count(),
        'preparing_orders': customer_orders.filter(shipping_status='preparing').count(),
        'shipped_orders': customer_orders.filter(shipping_status='shipped').count(),
        'in_transit_orders': customer_orders.filter(shipping_status='in_transit').count(),
        'delivered_orders': customer_orders.filter(shipping_status='delivered').count(),
    }
    
    # Get work orders for backward compatibility (if still using work order system)
    work_orders = factory_user.get_supplier_work_orders()
    
    # Recent work orders
    recent_orders = work_orders[:10]
    
    # Get customer invoices that have items from this supplier
    # Filter invoices that have at least one item with product from this supplier
    from sales.models import InvoiceItem
    customer_invoice_items = InvoiceItem.objects.filter(
        product__supplier=factory_user.supplier
    ).select_related(
        'invoice', 'invoice__customer', 'product'
    ).order_by('-invoice__created_at')[:20]  # Get recent 20 items
    
    # Pending supply requests
    pending_supplies = SupplyRequest.objects.filter(
        product__supplier=factory_user.supplier,
        status='pending'
    ).order_by('-urgency', 'needed_by')[:5]
    
    # Recent shipments
    recent_shipments = Shipment.objects.filter(
        work_order__in=work_orders
    ).order_by('-created_date')[:5]
    
    context = {
        'factory_user': factory_user,
        'stats': stats,
        'recent_orders': recent_orders,
        'customer_invoice_items': customer_invoice_items,
        'pending_supplies': pending_supplies,
        'recent_shipments': recent_shipments,
    }
    
    return render(request, 'factory_portal/dashboard.html', context)


@factory_user_required
def work_order_list(request):
    """List all customer orders (invoices) that contain products from the factory user's supplier"""
    factory_user = request.user.factory_profile
    
    # Get invoices that have items from this supplier
    from django.db.models import Exists, OuterRef, Prefetch
    from sales.models import InvoiceItem
    
    # Subquery to check if invoice has items from this supplier
    has_supplier_items = InvoiceItem.objects.filter(
        invoice=OuterRef('pk'),
        product__supplier=factory_user.supplier
    )
    
    # Get invoices with items from this supplier
    invoices = Invoice.objects.filter(
        Exists(has_supplier_items)
    ).select_related('customer').prefetch_related(
        Prefetch('items', 
                 queryset=InvoiceItem.objects.filter(product__supplier=factory_user.supplier),
                 to_attr='supplier_items')
    ).order_by('-created_at')
    
    # For each invoice, check if there's a related PO created by this factory
    for invoice in invoices:
        # Look for POs that reference this invoice in their notes
        related_po = PurchaseOrder.objects.filter(
            supplier=factory_user.supplier,
            notes__contains=f"[Invoice ID: {invoice.id}]"
        ).first()
        invoice.related_po = related_po  # Attach to invoice object for template use
    
    # Filter by shipping status
    status_filter = request.GET.get('status')
    if status_filter:
        invoices = invoices.filter(shipping_status=status_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(invoices, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Shipping status choices for filter
    shipping_status_choices = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    
    context = {
        'invoices': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'status_filter': status_filter,
        'search': search,
        'status_choices': shipping_status_choices,
    }
    
    return render(request, 'factory_portal/work_order_list.html', context)


@factory_user_required
def work_order_detail(request, pk):
    """View and manage work order details"""
    factory_user = request.user.factory_profile
    work_order = get_object_or_404(WorkOrder, pk=pk)
    
    # Check access permission
    if not factory_user.can_access_work_order(work_order):
        return HttpResponseForbidden("You don't have access to this work order.")
    
    # Get fulfillment items for this supplier's products only
    fulfillment_items = work_order.fulfillment_items.filter(
        invoice_item__product__supplier=factory_user.supplier
    )
    
    # Get shipments
    shipments = work_order.shipments.all()
    
    # Get supply requests
    supply_requests = work_order.supply_requests.filter(
        product__supplier=factory_user.supplier
    )
    
    context = {
        'work_order': work_order,
        'fulfillment_items': fulfillment_items,
        'shipments': shipments,
        'supply_requests': supply_requests,
        'can_manage': factory_user.role in ['manager', 'supervisor'],
        'can_ship': factory_user.can_create_shipments,
    }
    
    return render(request, 'factory_portal/work_order_detail.html', context)


@factory_user_required
def update_work_order_status(request, pk):
    """Update work order status"""
    factory_user = request.user.factory_profile
    
    # Check permissions
    if factory_user.role not in ['manager', 'supervisor']:
        return HttpResponseForbidden("You don't have permission to update work orders.")
    
    work_order = get_object_or_404(WorkOrder, pk=pk)
    
    # Check access
    if not factory_user.can_access_work_order(work_order):
        return HttpResponseForbidden("You don't have access to this work order.")
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(WorkOrder.STATUS_CHOICES):
            work_order.status = new_status
            if new_status == 'in_progress' and not work_order.start_date:
                work_order.start_date = timezone.now()
            elif new_status == 'completed':
                work_order.completion_date = timezone.now()
            work_order.save()
            
            messages.success(request, f'Work order status updated to {work_order.get_status_display()}')
        
        return redirect('factory_portal:work_order_detail', pk=pk)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@factory_user_required
def fulfillment_item_update(request, work_order_pk, item_pk):
    """Update fulfillment item status"""
    factory_user = request.user.factory_profile
    work_order = get_object_or_404(WorkOrder, pk=work_order_pk)
    
    # Check access
    if not factory_user.can_access_work_order(work_order):
        return HttpResponseForbidden("You don't have access to this work order.")
    
    item = get_object_or_404(
        FulfillmentItem,
        pk=item_pk,
        work_order=work_order,
        invoice_item__product__supplier=factory_user.supplier
    )
    
    if request.method == 'POST':
        form = FulfillmentItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save(commit=False)
            
            # Update tracking fields
            if item.status == 'allocated' and not item.allocated_by:
                item.allocated_by = request.user
                item.allocated_date = timezone.now()
            elif item.status == 'fulfilled' and not item.fulfilled_by:
                item.fulfilled_by = request.user
                item.fulfilled_date = timezone.now()
            
            item.save()
            messages.success(request, 'Fulfillment item updated successfully!')
            return redirect('factory_portal:work_order_detail', pk=work_order_pk)
    else:
        form = FulfillmentItemForm(instance=item)
    
    context = {
        'form': form,
        'work_order': work_order,
        'item': item,
    }
    
    return render(request, 'factory_portal/fulfillment_item_form.html', context)


@factory_user_required
def create_shipment(request, work_order_pk):
    """Create a new shipment for work order"""
    factory_user = request.user.factory_profile
    
    # Check permissions
    if not factory_user.can_create_shipments:
        return HttpResponseForbidden("You don't have permission to create shipments.")
    
    work_order = get_object_or_404(WorkOrder, pk=work_order_pk)
    
    # Check access
    if not factory_user.can_access_work_order(work_order):
        return HttpResponseForbidden("You don't have access to this work order.")
    
    if request.method == 'POST':
        form = ShipmentForm(request.POST)
        if form.is_valid():
            shipment = form.save(commit=False)
            shipment.work_order = work_order
            shipment.created_by = request.user
            shipment.save()
            
            messages.success(request, 'Shipment created successfully!')
            return redirect('factory_portal:work_order_detail', pk=work_order_pk)
    else:
        # Pre-populate shipping address from invoice
        invoice = work_order.invoice
        initial_data = {}
        
        if invoice.shipping_same_as_billing:
            initial_data = {
                'ship_to_name': invoice.customer.get_full_name() if invoice.customer else f"{invoice.first_name} {invoice.last_name}",
                'ship_to_company': invoice.customer.company_name if invoice.customer else "",
                'ship_to_address_line1': invoice.billing_address_line1,
                'ship_to_address_line2': invoice.billing_address_line2,
                'ship_to_city': invoice.billing_city,
                'ship_to_state': invoice.billing_state,
                'ship_to_postal_code': invoice.billing_postal_code,
                'ship_to_country': invoice.billing_country,
            }
        else:
            initial_data = {
                'ship_to_name': invoice.customer.get_full_name() if invoice.customer else f"{invoice.first_name} {invoice.last_name}",
                'ship_to_company': invoice.customer.company_name if invoice.customer else "",
                'ship_to_address_line1': invoice.shipping_address_line1,
                'ship_to_address_line2': invoice.shipping_address_line2,
                'ship_to_city': invoice.shipping_city,
                'ship_to_state': invoice.shipping_state,
                'ship_to_postal_code': invoice.shipping_postal_code,
                'ship_to_country': invoice.shipping_country,
            }
        
        form = ShipmentForm(initial=initial_data)
    
    context = {
        'form': form,
        'work_order': work_order,
    }
    
    return render(request, 'factory_portal/shipment_form.html', context)


@factory_user_required
def shipment_list(request):
    """List all shipments for the factory"""
    factory_user = request.user.factory_profile
    
    # Get work orders for this supplier
    work_orders = factory_user.get_supplier_work_orders()
    
    # Get shipments
    shipments = Shipment.objects.filter(work_order__in=work_orders)
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        shipments = shipments.filter(status=status_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        shipments = shipments.filter(
            Q(shipment_number__icontains=search) |
            Q(tracking_number__icontains=search) |
            Q(work_order__work_order_number__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(shipments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'shipments': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'status_filter': status_filter,
        'search': search,
        'status_choices': Shipment.STATUS_CHOICES,
    }
    
    return render(request, 'factory_portal/shipment_list.html', context)


@factory_user_required
def supply_request_list(request):
    """List supply requests for the factory"""
    factory_user = request.user.factory_profile
    
    # Get supply requests for this supplier's products
    requests = SupplyRequest.objects.filter(
        product__supplier=factory_user.supplier
    )
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    # Filter by urgency
    urgency_filter = request.GET.get('urgency')
    if urgency_filter:
        requests = requests.filter(urgency=urgency_filter)
    
    # Pagination
    paginator = Paginator(requests, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'supply_requests': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'status_choices': SupplyRequest.STATUS_CHOICES,
        'urgency_choices': SupplyRequest.URGENCY_CHOICES,
        'can_approve': factory_user.can_approve_supply_requests,
    }
    
    return render(request, 'factory_portal/supply_request_list.html', context)


@factory_user_required
def profile_view(request):
    """View and edit factory user profile"""
    factory_user = request.user.factory_profile
    
    if request.method == 'POST':
        form = FactoryProfileForm(request.POST, instance=factory_user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('factory_portal:profile')
    else:
        form = FactoryProfileForm(instance=factory_user)
    
    context = {
        'form': form,
        'factory_user': factory_user,
    }
    
    return render(request, 'factory_portal/profile.html', context)


@factory_user_required
def change_password(request):
    """Change password view"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('factory_portal:dashboard')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'factory_portal/change_password.html', {'form': form})


@factory_user_required
def ship_order(request):
    """Mark an order as shipped"""
    if request.method == 'POST':
        factory_user = request.user.factory_profile
        invoice_id = request.POST.get('invoice_id')
        tracking_number = request.POST.get('tracking_number', '')
        carrier = request.POST.get('carrier', '')
        notes = request.POST.get('notes', '')
        
        # Get the invoice
        invoice = get_object_or_404(Invoice, pk=invoice_id)
        
        # Check if this invoice has items from the factory user's supplier
        has_supplier_items = invoice.items.filter(
            product__supplier=factory_user.supplier
        ).exists()
        
        if not has_supplier_items:
            messages.error(request, "You don't have permission to ship this order.")
            return redirect('factory_portal:work_order_list')
        
        # Update invoice shipping status to shipped
        invoice.shipping_status = 'shipped'
        
        # Store tracking info if provided
        if tracking_number:
            invoice.post_tracking_number = tracking_number
        
        if carrier:
            # Map carrier to delivery service
            carrier_map = {
                'ups': 'ups',
                'fedex': 'fedex',
                'usps': 'usps',
                'dhl': 'dhl',
                'other': 'other'
            }
            if carrier in carrier_map:
                invoice.delivery_service = carrier_map[carrier]
        
        # Add notes to invoice notes if provided
        if notes:
            current_notes = invoice.notes or ''
            ship_note = f"\n\n[Shipping Note from {factory_user.supplier.name}]: {notes}"
            invoice.notes = current_notes + ship_note
        
        invoice.save()
        
        messages.success(request, f'Order {invoice.invoice_number} has been marked as shipped.')
        return redirect('factory_portal:work_order_list')
    
    return redirect('factory_portal:work_order_list')


@factory_user_required
def packing_slip(request, invoice_id):
    """View packing slip for an invoice (without price information)"""
    factory_user = request.user.factory_profile
    
    # Get the invoice
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    
    # Get only items from the factory user's supplier
    supplier_items = invoice.items.filter(
        product__supplier=factory_user.supplier
    ).select_related('product', 'inventory')
    
    # If no items from this supplier, deny access
    if not supplier_items.exists():
        return HttpResponseForbidden("You don't have access to this packing slip.")
    
    context = {
        'invoice': invoice,
        'invoice_items': supplier_items,  # Only show items from this supplier
        'supplier_items': supplier_items,  # Same items for compatibility
        'factory_user': factory_user,
        'is_packing_slip': True,  # Flag to hide prices in template
        'filtered_view': True,  # Flag to indicate this is a filtered view
    }
    
    return render(request, 'factory_portal/packing_slip.html', context)


@factory_user_required
def create_invoice(request):
    """Create a Purchase Order for the factory to bill the dental company"""
    if request.method == 'POST':
        factory_user = request.user.factory_profile
        invoice_id = request.POST.get('invoice_id')
        notes = request.POST.get('notes', '')
        
        # Get shipping cost if provided
        shipping_cost_str = request.POST.get('shipping_cost', '0')
        try:
            shipping_cost = Decimal(shipping_cost_str) if shipping_cost_str else Decimal('0.00')
        except (ValueError, TypeError):
            shipping_cost = Decimal('0.00')
        
        # Get the customer invoice
        invoice = get_object_or_404(Invoice, pk=invoice_id)
        
        # Get only items from this supplier
        invoice_items = invoice.items.filter(
            product__supplier=factory_user.supplier
        ).select_related('product')
        
        if not invoice_items.exists():
            messages.error(request, "No items from your supplier found in this order.")
            return redirect('factory_portal:work_order_list')
        
        # Generate PO number (you might want to customize this format)
        last_po = PurchaseOrder.objects.order_by('-id').first()
        if last_po:
            po_number = f"PO-{last_po.id + 1:06d}"
        else:
            po_number = "PO-000001"
        
        # Prepare notes
        po_notes = f"Purchase Order for Customer Invoice #{invoice.invoice_number}"
        po_notes += f"\n[Invoice ID: {invoice.id}]"  # Store invoice ID for reference
        if notes:
            po_notes += f"\n{notes}"
        
        # Create the Purchase Order with shipping cost
        purchase_order = PurchaseOrder.objects.create(
            order_number=po_number,  # Fixed: use order_number instead of purchase_order_number
            supplier=factory_user.supplier,
            status='sent',  # Automatically mark as sent since it's for billing
            order_date=timezone.now().date(),
            expected_delivery_date=timezone.now().date() + timedelta(days=30),  # 30 days payment terms
            subtotal=Decimal('0.00'),
            tax_rate=Decimal('0.00'),
            tax_amount=Decimal('0.00'),
            shipping_cost=shipping_cost,  # Set the shipping cost here
            discount_percent=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('0.00'),
            notes=po_notes,
            created_by=request.user
        )
        
        # Create PO items from invoice items (using product cost, not retail price)
        subtotal = Decimal('0.00')
        for invoice_item in invoice_items:
            # Use product cost (wholesale price) instead of invoice unit price (retail price)
            if invoice_item.product and invoice_item.product.cost:
                unit_cost = Decimal(str(invoice_item.product.cost))
            else:
                # Fallback to invoice price if cost is not set (shouldn't happen normally)
                unit_cost = invoice_item.unit_price
            
            # Calculate line total (no discount in PO model)
            quantity = Decimal(str(invoice_item.quantity))
            line_total = quantity * unit_cost
            
            po_item = PurchaseOrderItem.objects.create(
                purchase_order=purchase_order,
                product=invoice_item.product,
                description=invoice_item.description,
                quantity=invoice_item.quantity,
                unit_cost=unit_cost,  # Product cost (wholesale price)
                line_total=line_total
            )
            subtotal += po_item.line_total
        
        # Update PO totals (subtotal + shipping = total)
        purchase_order.subtotal = subtotal
        purchase_order.total_amount = subtotal + shipping_cost
        purchase_order.save()
        
        # Create success message
        total_amount = subtotal + shipping_cost
        success_msg = f'Purchase Order #{po_number} has been created successfully for billing. '
        success_msg += f'Subtotal: ${subtotal:,.2f} (at cost prices)'
        if shipping_cost > 0:
            success_msg += f', Shipping: ${shipping_cost:,.2f}'
        success_msg += f', Total: ${total_amount:,.2f}'
        success_msg += f'. The accounting department will process this PO for payment.'
        messages.success(request, success_msg)
        
        # Redirect back to work order list (factory users don't have access to purchase order detail)
        return redirect('factory_portal:work_order_list')
    
    return redirect('factory_portal:work_order_list')


@factory_user_required
def view_billing_invoice(request, po_id):
    """View billing invoice (Purchase Order) created by factory user"""
    factory_user = request.user.factory_profile
    
    # Get the PO and verify it belongs to this factory's supplier
    purchase_order = get_object_or_404(
        PurchaseOrder, 
        pk=po_id,
        supplier=factory_user.supplier
    )
    
    # Get PO items
    po_items = purchase_order.items.select_related('product').all()
    
    # Extract the original invoice reference from notes if available
    original_invoice = None
    if "[Invoice ID:" in purchase_order.notes:
        try:
            invoice_id_str = purchase_order.notes.split("[Invoice ID: ")[1].split("]")[0]
            original_invoice = Invoice.objects.get(pk=int(invoice_id_str))
        except (IndexError, ValueError, Invoice.DoesNotExist):
            pass
    
    context = {
        'purchase_order': purchase_order,
        'po_items': po_items,
        'original_invoice': original_invoice,
        'factory_user': factory_user,
        'is_billing_view': True,  # Flag to indicate this is a billing view
    }
    
    return render(request, 'factory_portal/billing_invoice.html', context)
