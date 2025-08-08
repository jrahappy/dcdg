from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, F
from django.http import JsonResponse
from django.urls import reverse
from .models import Product, ProductDoc, ProductImage, Inventory, ProductOptionName, ProductOptionItem, ProductOption, Category
from .forms import ProductForm, ProductSearchForm
import json


@staff_member_required
def product_list(request):
    products = Product.objects.prefetch_related('images').all()
    form = ProductSearchForm(request.GET)

    # Apply filters
    if form.is_valid():
        search = form.cleaned_data.get("search")
        category = form.cleaned_data.get("category")
        status = form.cleaned_data.get("status")
        is_featured = form.cleaned_data.get("is_featured")

        if search:
            products = products.filter(
                Q(name__icontains=search)
                | Q(sku__icontains=search)
                | Q(brand__icontains=search)
                | Q(manufacturer__icontains=search)
                | Q(short_description__icontains=search)
                | Q(tags__icontains=search)
            )

        if category:
            products = products.filter(category=category)

        if status:
            products = products.filter(status=status)

        if is_featured:
            if is_featured == "true":
                products = products.filter(is_featured=True)
            elif is_featured == "false":
                products = products.filter(is_featured=False)

    # Order by created date
    products = products.order_by("-created_at")

    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get statistics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(status="active").count()
    low_stock_products = Product.objects.filter(
        quantity_in_stock__lte=F("minimum_stock_level")
    ).count()

    context = {
        "page_obj": page_obj,
        "form": form,
        "total_products": total_products,
        "active_products": active_products,
        "low_stock_products": low_stock_products,
    }

    return render(request, "product/product_list_daisyui.html", context)


@staff_member_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Increment view count
    product.views_count += 1
    product.save(update_fields=["views_count"])

    # Get related data
    documents = product.documents.all()
    images = product.images.all()
    inventory_items = product.inventory_items.all()[:10]  # Show last 10 items
    product_options = ProductOption.objects.filter(product=product, is_active=True).select_related('option_name')

    # Calculate inventory statistics
    total_inventory = product.inventory_items.count()
    available_inventory = product.inventory_items.filter(status="available").count()
    sold_inventory = product.inventory_items.filter(status="sold").count()

    context = {
        "product": product,
        "documents": documents,
        "images": images,
        "inventory_items": inventory_items,
        "product_options": product_options,
        "total_inventory": total_inventory,
        "available_inventory": available_inventory,
        "sold_inventory": sold_inventory,
    }

    return render(request, "product/product_detail.html", context)


@staff_member_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user

            # Handle specifications
            specifications = form.cleaned_data.get("specifications", {})
            product.specifications = specifications

            product.save()
            
            # Handle product options
            selected_options = form.cleaned_data.get('product_options', [])
            # Remove existing options
            ProductOption.objects.filter(product=product).delete()
            # Add selected options
            for option_name in selected_options:
                ProductOption.objects.create(
                    product=product,
                    option_name=option_name,
                    is_active=True
                )
            
            messages.success(
                request, f'Product "{product.name}" has been created successfully.'
            )
            return redirect("product:product_detail", pk=product.pk)
    else:
        form = ProductForm()

    return render(
        request,
        "product/product_form.html",
        {"form": form, "title": "Create New Product", "button_text": "Create Product"},
    )


@staff_member_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)

            # Handle specifications
            specifications = form.cleaned_data.get("specifications", {})
            product.specifications = specifications

            product.save()
            
            # Handle product options
            selected_options = form.cleaned_data.get('product_options', [])
            # Remove existing options
            ProductOption.objects.filter(product=product).delete()
            # Add selected options
            for option_name in selected_options:
                ProductOption.objects.create(
                    product=product,
                    option_name=option_name,
                    is_active=True
                )
            
            messages.success(
                request, f'Product "{product.name}" has been updated successfully.'
            )
            return redirect("product:product_detail", pk=product.pk)
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "product/product_form.html",
        {
            "form": form,
            "product": product,
            "title": f"Edit Product: {product.name}",
            "button_text": "Update Product",
        },
    )


@staff_member_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        product_name = product.name
        product.delete()
        messages.success(
            request, f'Product "{product_name}" has been deleted successfully.'
        )
        return redirect("product:product_list")

    # Check if product has inventory items
    inventory_count = product.inventory_items.count()

    return render(
        request,
        "product/product_confirm_delete.html",
        {
            "product": product,
            "inventory_count": inventory_count,
        },
    )


@staff_member_required
def product_duplicate(request, pk):
    """Duplicate a product"""
    original_product = get_object_or_404(Product, pk=pk)

    # Create a copy of the product
    new_product = Product(
        name=f"{original_product.name} (Copy)",
        sku=f"{original_product.sku}-COPY",
        category=original_product.category,
        brand=original_product.brand,
        manufacturer=original_product.manufacturer,
        short_description=original_product.short_description,
        long_description=original_product.long_description,
        features=original_product.features,
        specifications=original_product.specifications,
        price=original_product.price,
        cost=original_product.cost,
        discount_percentage=original_product.discount_percentage,
        quantity_in_stock=0,  # Start with 0 stock
        minimum_stock_level=original_product.minimum_stock_level,
        weight=original_product.weight,
        dimensions=original_product.dimensions,
        status="draft",  # Set as draft
        is_featured=False,
        tags=original_product.tags,
        is_serial_number_managed=original_product.is_serial_number_managed,
        created_by=request.user,
    )

    new_product.save()

    messages.success(
        request,
        f"Product duplicated successfully. Please update the SKU and other details.",
    )
    return redirect("product:product_update", pk=new_product.pk)


@staff_member_required
def product_quick_update(request, pk):
    """Quick update for stock and price via AJAX"""
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk)

        try:
            data = json.loads(request.body)

            if "quantity_in_stock" in data:
                product.quantity_in_stock = int(data["quantity_in_stock"])

            if "price" in data:
                product.price = float(data["price"])

            if "status" in data:
                product.status = data["status"]

            product.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": "Product updated successfully",
                    "is_low_stock": product.is_low_stock,
                    "display_price": str(product.display_price),
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=400)

    return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)


@staff_member_required
def product_image_delete(request, pk):
    """Delete a product image"""
    from .models import ProductImage
    
    image = get_object_or_404(ProductImage, pk=pk)
    product_id = image.product.id
    
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully.')
        return redirect('product:product_detail', pk=product_id)
    
    # For AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        image.delete()
        return JsonResponse({'success': True})
    
    return redirect('product:product_detail', pk=product_id)


# Inventory Views
@staff_member_required
def inventory_list(request):
    """List all inventory items with filters"""
    inventory_items = Inventory.objects.select_related(
        "product", "customer", "assigned_to"
    ).all()

    # Search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        inventory_items = inventory_items.filter(
            Q(serial_number__icontains=search_query)
            | Q(batch_number__icontains=search_query)
            | Q(product__name__icontains=search_query)
            | Q(product__sku__icontains=search_query)
            | Q(barcode__icontains=search_query)
            | Q(customer__first_name__icontains=search_query)
            | Q(customer__last_name__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get("status", "")
    if status_filter:
        inventory_items = inventory_items.filter(status=status_filter)

    # Filter by warranty status
    warranty_filter = request.GET.get("warranty_status", "")
    if warranty_filter:
        inventory_items = inventory_items.filter(warranty_status=warranty_filter)

    # Filter by product
    product_filter = request.GET.get("product", "")
    if product_filter:
        inventory_items = inventory_items.filter(product_id=product_filter)

    # Filter by purchase order
    po_filter = request.GET.get("purchase_order", "")
    if po_filter:
        inventory_items = inventory_items.filter(purchase_order_number=po_filter)

    # Order by created date
    inventory_items = inventory_items.order_by("-created_at")

    # Pagination
    paginator = Paginator(inventory_items, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get statistics - only current inventory (available items)
    from django.db.models import Sum, F
    
    # Count only available (in-stock) items
    current_count = Inventory.objects.filter(status="available").count()
    
    # Calculate total cost of available inventory
    # Using the product's cost field for inventory valuation
    total_cost = Inventory.objects.filter(
        status="available"
    ).aggregate(
        total=Sum(F('product__cost'))
    )['total'] or 0

    # Get products for filter dropdown
    products = Product.objects.filter(is_serial_number_managed=True).order_by("name")

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "warranty_filter": warranty_filter,
        "product_filter": product_filter,
        "current_count": current_count,
        "total_cost": total_cost,
        "products": products,
        "status_choices": Inventory.STATUS_CHOICES,
        "warranty_status_choices": Inventory.WARRANTY_STATUS_CHOICES,
        "is_paginated": page_obj.has_other_pages(),
    }

    return render(request, "product/inventory_list_daisyui.html", context)


@staff_member_required
def inventory_detail(request, pk):
    """View inventory item details"""
    inventory = get_object_or_404(
        Inventory.objects.select_related(
            "product", "customer", "assigned_to", "created_by"
        ),
        pk=pk,
    )

    # Try to find the related purchase order
    purchase_order = None
    if inventory.purchase_order_number:
        from purchases.models import PurchaseOrder

        try:
            purchase_order = PurchaseOrder.objects.get(
                order_number=inventory.purchase_order_number
            )
        except PurchaseOrder.DoesNotExist:
            pass

    # Try to find related invoice items
    invoice_items = inventory.invoice_items.select_related(
        "invoice", "invoice__customer"
    ).all()

    context = {
        "inventory": inventory,
        "purchase_order": purchase_order,
        "invoice_items": invoice_items,
    }

    return render(request, "product/inventory_detail.html", context)


@staff_member_required
def inventory_create(request):
    """Create new inventory item"""
    from .forms import InventoryForm

    if request.method == "POST":
        form = InventoryForm(request.POST)
        if form.is_valid():
            inventory = form.save(commit=False)
            inventory.created_by = request.user

            # Auto-calculate warranty end date if start date is provided but end date is not
            if inventory.warranty_start_date and not inventory.warranty_end_date:
                inventory.calculate_warranty_end_date(12)  # Default 12 months warranty

            inventory.save()

            # Update warranty status
            inventory.update_warranty_status()

            messages.success(
                request,
                f'Inventory item "{inventory.serial_number}" has been created successfully.',
            )
            return redirect("product:inventory_detail", pk=inventory.pk)
    else:
        # Pre-populate product if passed as query parameter
        product_id = request.GET.get("product")
        initial = {}
        if product_id:
            product = get_object_or_404(Product, pk=product_id)
            initial["product"] = product
            initial["purchase_price"] = product.cost

        form = InventoryForm(initial=initial)

    context = {
        "form": form,
        "title": "Add New Inventory Item",
        "button_text": "Add Item",
    }

    return render(request, "product/inventory_form_daisyui.html", context)


@staff_member_required
def inventory_update(request, pk):
    """Update inventory item"""
    from .forms import InventoryForm

    inventory = get_object_or_404(Inventory, pk=pk)

    if request.method == "POST":
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            inventory = form.save()

            # Update warranty status
            inventory.update_warranty_status()

            messages.success(
                request,
                f'Inventory item "{inventory.serial_number}" has been updated successfully.',
            )
            return redirect("product:inventory_detail", pk=inventory.pk)
    else:
        form = InventoryForm(instance=inventory)

    context = {
        "form": form,
        "inventory": inventory,
        "title": f"Edit Inventory: {inventory.serial_number}",
        "button_text": "Update Item",
    }

    return render(request, "product/inventory_form_daisyui.html", context)


@staff_member_required
def inventory_delete(request, pk):
    """Delete inventory item"""
    inventory = get_object_or_404(
        Inventory.objects.select_related("product", "customer").prefetch_related(
            "invoice_items"
        ),
        pk=pk,
    )

    print(inventory)

    if request.method == "POST":
        # Check if inventory is linked to invoices
        if inventory.invoice_items.exists():
            messages.error(
                request, "Cannot delete inventory item that is linked to invoices."
            )
            return redirect("product:inventory_detail", pk=pk)

        serial_number = inventory.serial_number
        inventory.delete()
        messages.success(
            request, f'Inventory item "{serial_number}" has been deleted successfully.'
        )
        return redirect("product:inventory_list")

    context = {
        "inventory": inventory,
    }

    return render(request, "product/inventory_confirm_delete.html", context)


# Product Option Views
@staff_member_required
def option_list(request):
    """List all product option names"""
    options = ProductOptionName.objects.all().annotate(
        item_count=Count('items')
    ).order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        options = options.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        options = options.filter(is_active=True)
    elif status_filter == 'inactive':
        options = options.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(options, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_options': ProductOptionName.objects.count(),
        'active_options': ProductOptionName.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'product/option_list_daisyui.html', context)


@staff_member_required
def option_detail(request, pk):
    """View option details with its items"""
    option = get_object_or_404(ProductOptionName, pk=pk)
    items = option.items.all().order_by('ordering', 'value')
    
    context = {
        'option': option,
        'items': items,
    }
    
    return render(request, 'product/option_detail.html', context)


@staff_member_required
def option_create(request):
    """Create new option name"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if not name:
            messages.error(request, 'Option name is required.')
            return redirect('product:option_create')
        
        # Check if option name already exists
        if ProductOptionName.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Option "{name}" already exists.')
            return redirect('product:option_create')
        
        option = ProductOptionName.objects.create(
            name=name,
            description=description,
            is_active=is_active
        )
        
        # Handle option items if provided
        item_values = request.POST.getlist('item_value[]')
        item_orderings = request.POST.getlist('item_ordering[]')
        
        for i, value in enumerate(item_values):
            if value.strip():
                ordering = item_orderings[i] if i < len(item_orderings) else i
                try:
                    ordering = int(ordering)
                except (ValueError, TypeError):
                    ordering = i
                    
                ProductOptionItem.objects.create(
                    option_name=option,
                    value=value.strip(),
                    ordering=ordering,
                    is_active=True
                )
        
        messages.success(request, f'Option "{option.name}" has been created successfully.')
        return redirect('product:option_detail', pk=option.pk)
    
    return render(request, 'product/option_form_daisyui.html', {
        'title': 'Create New Option',
        'button_text': 'Create Option'
    })


@staff_member_required
def option_update(request, pk):
    """Update option name"""
    option = get_object_or_404(ProductOptionName, pk=pk)
    
    if request.method == 'POST':
        option.name = request.POST.get('name', '').strip()
        option.description = request.POST.get('description', '').strip()
        option.is_active = request.POST.get('is_active') == 'on'
        
        if not option.name:
            messages.error(request, 'Option name is required.')
            return redirect('product:option_update', pk=pk)
        
        # Check if another option with same name exists
        if ProductOptionName.objects.filter(name__iexact=option.name).exclude(pk=pk).exists():
            messages.error(request, f'Another option with name "{option.name}" already exists.')
            return redirect('product:option_update', pk=pk)
        
        option.save()
        
        # Handle option items
        # Delete removed items
        existing_item_ids = request.POST.getlist('existing_item_id[]')
        option.items.exclude(pk__in=existing_item_ids).delete()
        
        # Update existing items
        item_values = request.POST.getlist('item_value[]')
        item_orderings = request.POST.getlist('item_ordering[]')
        item_active = request.POST.getlist('item_active[]')
        
        # Update existing items
        for item_id in existing_item_ids:
            if item_id:
                try:
                    item = ProductOptionItem.objects.get(pk=item_id, option_name=option)
                    index = existing_item_ids.index(item_id)
                    if index < len(item_values):
                        item.value = item_values[index].strip()
                        item.ordering = int(item_orderings[index]) if index < len(item_orderings) else index
                        item.is_active = str(item_id) in item_active
                        item.save()
                except (ProductOptionItem.DoesNotExist, ValueError):
                    pass
        
        # Add new items
        new_item_values = request.POST.getlist('new_item_value[]')
        new_item_orderings = request.POST.getlist('new_item_ordering[]')
        
        for i, value in enumerate(new_item_values):
            if value.strip():
                ordering = new_item_orderings[i] if i < len(new_item_orderings) else i
                try:
                    ordering = int(ordering)
                except (ValueError, TypeError):
                    ordering = i
                    
                ProductOptionItem.objects.create(
                    option_name=option,
                    value=value.strip(),
                    ordering=ordering,
                    is_active=True
                )
        
        messages.success(request, f'Option "{option.name}" has been updated successfully.')
        return redirect('product:option_detail', pk=option.pk)
    
    items = option.items.all().order_by('ordering', 'value')
    
    return render(request, 'product/option_form_daisyui.html', {
        'option': option,
        'items': items,
        'title': f'Edit Option: {option.name}',
        'button_text': 'Update Option'
    })


@staff_member_required
def option_delete(request, pk):
    """Delete option name"""
    option = get_object_or_404(ProductOptionName, pk=pk)
    
    if request.method == 'POST':
        option_name = option.name
        option.delete()
        messages.success(request, f'Option "{option_name}" has been deleted successfully.')
        return redirect('product:option_list')
    
    # Check if option is used by any products
    product_count = option.product_options.count()
    
    context = {
        'option': option,
        'product_count': product_count,
        'item_count': option.items.count(),
    }
    
    return render(request, 'product/option_confirm_delete.html', context)


@staff_member_required
def option_item_create(request, option_pk):
    """Add new item to an option (AJAX)"""
    if request.method == 'POST':
        option = get_object_or_404(ProductOptionName, pk=option_pk)
        
        value = request.POST.get('value', '').strip()
        ordering = request.POST.get('ordering', 0)
        
        if not value:
            return JsonResponse({'success': False, 'message': 'Value is required'})
        
        # Check if item already exists
        if option.items.filter(value__iexact=value).exists():
            return JsonResponse({'success': False, 'message': f'Item "{value}" already exists'})
        
        try:
            ordering = int(ordering)
        except (ValueError, TypeError):
            ordering = 0
        
        item = ProductOptionItem.objects.create(
            option_name=option,
            value=value,
            ordering=ordering,
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.pk,
                'value': item.value,
                'ordering': item.ordering,
                'is_active': item.is_active
            }
        })
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'})


@staff_member_required
def option_item_delete(request, pk):
    """Delete option item (AJAX)"""
    if request.method == 'POST':
        item = get_object_or_404(ProductOptionItem, pk=pk)
        item.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'})


# Category Views
@staff_member_required
def category_list(request):
    """List all product categories"""
    categories = Category.objects.filter(parent__isnull=True).order_by('order', 'name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        categories = Category.objects.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        ).order_by('order', 'name')
    
    # Get all categories for tree view
    all_categories = Category.objects.all().order_by('order', 'name').prefetch_related('children', 'products')
    
    # Add product count to each category
    for category in all_categories:
        category.product_count = category.products.count()
        # Count products in children too
        for child in category.get_descendants():
            category.product_count += child.products.count()
    
    context = {
        'categories': categories,
        'all_categories': all_categories,
        'search_query': search_query,
    }
    
    return render(request, 'product/category_list.html', context)


@staff_member_required
def category_create(request):
    """Create a new product category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        parent_id = request.POST.get('parent')
        description = request.POST.get('description', '')
        icon = request.POST.get('icon', '')
        is_active = 'is_active' in request.POST
        order = request.POST.get('order', 0)
        
        try:
            order = int(order)
        except (ValueError, TypeError):
            order = 0
        
        parent = None
        if parent_id:
            parent = get_object_or_404(Category, pk=parent_id)
        
        category = Category(
            name=name,
            parent=parent,
            description=description,
            icon=icon,
            is_active=is_active,
            order=order
        )
        category.save()
        
        messages.success(request, f'Category "{category.name}" has been created successfully.')
        return redirect('product:category_detail', pk=category.pk)
    
    categories = Category.objects.filter(is_active=True)
    context = {
        'categories': categories,
    }
    
    return render(request, 'product/category_form.html', context)


@staff_member_required
def category_detail(request, pk):
    """View category details"""
    category = get_object_or_404(Category, pk=pk)
    
    # Get products in this category
    products = category.products.all()
    
    # Get subcategories
    subcategories = category.children.all()
    
    # Get ancestors for breadcrumb
    ancestors = category.get_ancestors()
    
    context = {
        'category': category,
        'products': products,
        'subcategories': subcategories,
        'ancestors': ancestors,
    }
    
    return render(request, 'product/category_detail.html', context)


@staff_member_required
def category_update(request, pk):
    """Update a product category"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category.name = request.POST.get('name', category.name)
        category.description = request.POST.get('description', '')
        category.icon = request.POST.get('icon', '')
        category.is_active = 'is_active' in request.POST
        
        try:
            category.order = int(request.POST.get('order', 0))
        except (ValueError, TypeError):
            category.order = 0
        
        parent_id = request.POST.get('parent')
        if parent_id:
            parent = get_object_or_404(Category, pk=parent_id)
            # Prevent setting self or descendants as parent
            if parent != category and parent not in category.get_descendants():
                category.parent = parent
        else:
            category.parent = None
        
        category.save()
        
        messages.success(request, f'Category "{category.name}" has been updated successfully.')
        return redirect('product:category_detail', pk=category.pk)
    
    # Get all categories except self and its descendants for parent selection
    available_parents = Category.objects.exclude(pk=category.pk)
    for descendant in category.get_descendants():
        available_parents = available_parents.exclude(pk=descendant.pk)
    
    context = {
        'category': category,
        'categories': available_parents,
    }
    
    return render(request, 'product/category_form.html', context)


@staff_member_required
def category_delete(request, pk):
    """Delete a product category"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category_name = category.name
        
        # Check what to do with products
        action = request.POST.get('action', 'move')
        if action == 'move' and category.parent:
            # Move products to parent category
            category.products.update(category=category.parent)
        elif action == 'unassign':
            # Remove category from products
            category.products.update(category=None)
        
        # Move child categories to parent
        if category.parent:
            category.children.update(parent=category.parent)
        else:
            category.children.update(parent=None)
        
        category.delete()
        
        messages.success(request, f'Category "{category_name}" has been deleted successfully.')
        return redirect('product:category_list')
    
    context = {
        'category': category,
        'product_count': category.products.count(),
        'subcategory_count': category.children.count(),
    }
    
    return render(request, 'product/category_confirm_delete.html', context)


# Product Upload Views
@staff_member_required
def product_upload_image(request, pk):
    """Handle product image upload"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        caption = request.POST.get('caption', '')
        is_primary = request.POST.get('is_primary') == 'on'
        
        if image_file:
            # If setting as primary, unset other primary images
            if is_primary:
                product.images.update(is_primary=False)
            
            # Create new image
            from product.models import ProductImage
            ProductImage.objects.create(
                product=product,
                image=image_file,
                caption=caption,
                is_primary=is_primary,
                order=product.images.count()
            )
            
            messages.success(request, 'Image uploaded successfully.')
        else:
            messages.error(request, 'No image file provided.')
    
    return redirect('product:product_detail', pk=pk)


@staff_member_required  
def product_upload_document(request, pk):
    """Handle product document upload"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        doc_type = request.POST.get('doc_type', 'other')
        description = request.POST.get('description', '')
        is_public = request.POST.get('is_public') == 'on'
        doc_file = request.FILES.get('file')
        
        if doc_file and title:
            # Get file size
            file_size = doc_file.size
            
            # Create new document
            from product.models import ProductDoc
            ProductDoc.objects.create(
                product=product,
                title=title,
                doc_type=doc_type,
                description=description,
                file=doc_file,
                file_size=file_size,
                is_public=is_public,
                uploaded_by=request.user
            )
            
            messages.success(request, 'Document uploaded successfully.')
        else:
            messages.error(request, 'Title and document file are required.')
    
    return redirect('product:product_detail', pk=pk)
