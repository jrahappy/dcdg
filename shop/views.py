# Standard library imports
from datetime import timedelta
from decimal import Decimal
import json

# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string

# App/model imports
from product.models import Product, Category, ProductOption, ProductOptionItem
from sales.models import Invoice, InvoiceItem
from .models import Cart, CartItem, ShippingRate, PromoCode
from blog.models import Post, Category as BlogCategory
from pages.models import NavMenu
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from decimal import Decimal
import traceback
from datetime import timedelta
from decimal import Decimal
from itertools import groupby
from operator import attrgetter


from product.models import Product, Category, ProductOption, ProductOptionItem
from sales.models import Invoice, InvoiceItem
from .models import Cart, CartItem, ShippingRate, PromoCode
from blog.models import Post, Category as BlogCategory
from pages.models import NavMenu
from customer.models import CustomerAddress


def index(request):
    """Display products for shopping"""
    # Optimize query with select_related for ForeignKeys and prefetch_related for reverse ForeignKeys
    queryset = (
        Product.objects.filter(status="active")
        .select_related(
            "category",  # ForeignKey to Category
            "supplier",  # ForeignKey to Supplier (if needed)
        )
        .prefetch_related(
            "images",  # Prefetch related ProductImage objects
        )
    )

    # Search
    search = request.GET.get("search")
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(short_description__icontains=search)
            | Q(long_description__icontains=search)
            | Q(sku__icontains=search)
        )

    # Category filter
    category_id = request.GET.get("category")
    if category_id:
        try:
            category = Category.objects.get(pk=category_id, is_active=True)
            # Get all active descendant categories
            descendant_ids = [category.id]
            descendants = list(category.children.filter(is_active=True))
            while descendants:
                child = descendants.pop()
                descendant_ids.append(child.id)
                descendants.extend(list(child.children.filter(is_active=True)))
            queryset = queryset.filter(category_id__in=descendant_ids)
        except Category.DoesNotExist:
            pass

    # Sort
    sort = request.GET.get("sort", "-created_at")

    # Check if we should group by category
    group_by_category = request.GET.get("group_by_category", "false") == "true"

    if group_by_category:

        # Sort by category order first, then by product name (or selected sort)
        if sort in ["price", "-price", "name", "-name", "-created_at"]:
            queryset = queryset.order_by("category__order", "category__name", sort)
        else:
            # Default: order by category order, then by product name
            queryset = queryset.order_by("category__order", "category__name", "name")

        # Group products by category (only active categories)
        products_by_category = []
        for category, group in groupby(queryset, key=attrgetter("category")):
            if (
                category and category.is_active
            ):  # Only include products with active categories
                products_list = list(group)
                products_by_category.append(
                    {"category": category, "products": products_list}
                )

        # Pagination for grouped view (paginate categories, not individual products)
        paginator = Paginator(products_by_category, 3)  # Show 3 categories per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        products = None  # Not used in grouped view
    else:
        # Regular pagination for non-grouped view
        # Always apply category order first, then the selected sort
        if sort in ["price", "-price", "name", "-name", "-created_at"]:
            queryset = queryset.order_by("category__order", "category__name", sort)
        else:
            # Default: order by category order, then by product name
            queryset = queryset.order_by("category__order", "category__name", "name")

        paginator = Paginator(queryset, 32)
        page_number = request.GET.get("page")
        products = paginator.get_page(page_number)
        page_obj = products
        products_by_category = None

    # Optimize categories query - prefetch children if needed for nested navigation
    # Filter by is_active and sort by order field
    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("order", "name")
    )

    # Get related blog posts if a category is selected
    related_posts = None
    current_category = None
    if category_id:
        try:
            current_category = Category.objects.get(pk=category_id, is_active=True)
            # Get blog posts related to this product category

            related_posts = (
                Post.objects.filter(
                    product_category=current_category, status="published"
                )
                .select_related("author", "category")
                .order_by("-published_date")[:3]
            )
        except Category.DoesNotExist:
            pass

    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")

    context = {
        "products": products,
        "products_by_category": products_by_category if group_by_category else None,
        "categories": categories,
        "cart": get_cart(request),
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "group_by_category": group_by_category,
        "related_posts": related_posts,
        "current_category": current_category,
        "navbar_items": navbar_items,
    }

    return render(request, "shop/index.html", context)


def get_cart(request):
    """Get or create cart for the current session or user"""
    if not request.session.session_key:
        request.session.create()

    # For authenticated users, try to get their cart by user first
    if request.user.is_authenticated:
        # Try to find an existing cart for this user
        cart = (
            Cart.objects.filter(user=request.user)
            .prefetch_related(
                "items",  # Prefetch cart items
                "items__product",  # Prefetch products for each cart item
                "items__product__images",  # Prefetch product images for gallery
            )
            .first()
        )

        if cart:
            # Update session_key if it has changed (new session)
            if cart.session_key != request.session.session_key:
                cart.session_key = request.session.session_key
                cart.save(update_fields=["session_key"])
            return cart

        # If no cart exists for authenticated user, check if there's a recent anonymous cart
        # that might have been missed during login (fallback mechanism)
        old_session_key = request.session.get("_old_session_key", None)
        if old_session_key:
            anonymous_cart = (
                Cart.objects.filter(session_key=old_session_key, user__isnull=True)
                .prefetch_related(
                    "items",
                    "items__product",
                    "items__product__images",
                )
                .first()
            )

            if anonymous_cart:
                # Claim this cart for the user
                anonymous_cart.user = request.user
                anonymous_cart.session_key = request.session.session_key
                anonymous_cart.save(update_fields=["user", "session_key"])
                # Clean up the old session key reference
                del request.session["_old_session_key"]
                request.session.save()
                return anonymous_cart

    # For anonymous users or if no user cart exists, use session-based cart
    cart, created = Cart.objects.prefetch_related(
        "items",  # Prefetch cart items
        "items__product",  # Prefetch products for each cart item
        "items__product__images",  # Prefetch product images for gallery
    ).get_or_create(
        session_key=request.session.session_key,
        defaults={"user": request.user if request.user.is_authenticated else None},
    )

    # If user is authenticated and cart was just created, assign it to them
    if created and request.user.is_authenticated:
        cart.user = request.user
        cart.save(update_fields=["user"])

    return cart


def product_list(request):
    """Display products for shopping"""
    # Optimize query with select_related for ForeignKeys and prefetch_related for reverse ForeignKeys
    queryset = (
        Product.objects.filter(status="active")
        .select_related(
            "category",  # ForeignKey to Category
            "supplier",  # ForeignKey to Supplier (if needed)
        )
        .prefetch_related(
            "images",  # Prefetch related ProductImage objects
        )
    )

    # Search
    search = request.GET.get("search")
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(short_description__icontains=search)
            | Q(long_description__icontains=search)
            | Q(sku__icontains=search)
        )

    # Category filter
    category_id = request.GET.get("category")
    if category_id:
        try:
            category = Category.objects.get(pk=category_id, is_active=True)
            # Get all active descendant categories
            descendant_ids = [category.id]
            descendants = list(category.children.filter(is_active=True))
            while descendants:
                child = descendants.pop()
                descendant_ids.append(child.id)
                descendants.extend(list(child.children.filter(is_active=True)))
            queryset = queryset.filter(category_id__in=descendant_ids)
        except Category.DoesNotExist:
            pass

    # Sort
    sort = request.GET.get("sort", "-created_at")

    # Check if we should group by category
    group_by_category = request.GET.get("group_by_category", "false") == "true"

    if group_by_category:

        # Sort by category order first, then by product name (or selected sort)
        if sort in ["price", "-price", "name", "-name", "-created_at"]:
            queryset = queryset.order_by("category__order", "category__name", sort)
        else:
            # Default: order by category order, then by product name
            queryset = queryset.order_by("category__order", "category__name", "name")

        # Group products by category (only active categories)
        products_by_category = []
        for category, group in groupby(queryset, key=attrgetter("category")):
            if (
                category and category.is_active
            ):  # Only include products with active categories
                products_list = list(group)
                products_by_category.append(
                    {"category": category, "products": products_list}
                )

        # Pagination for grouped view (paginate categories, not individual products)
        paginator = Paginator(products_by_category, 3)  # Show 3 categories per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        products = None  # Not used in grouped view
    else:
        # Regular pagination for non-grouped view
        # Always apply category order first, then the selected sort
        if sort in ["price", "-price", "name", "-name", "-created_at"]:
            queryset = queryset.order_by("category__order", "category__name", sort)
        else:
            # Default: order by category order, then by product name
            queryset = queryset.order_by("category__order", "category__name", "name")

        paginator = Paginator(queryset, 32)
        page_number = request.GET.get("page")
        products = paginator.get_page(page_number)
        page_obj = products
        products_by_category = None

    # Optimize categories query - prefetch children if needed for nested navigation
    # Filter by is_active and sort by order field
    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("order", "name")
    )

    # Get related blog posts if a category is selected
    related_posts = None
    current_category = None
    if category_id:
        try:
            current_category = Category.objects.get(pk=category_id, is_active=True)
            # Get blog posts related to this product category

            related_posts = (
                Post.objects.filter(
                    product_category=current_category, status="published"
                )
                .select_related("author", "category")
                .order_by("-published_date")[:3]
            )
        except Category.DoesNotExist:
            pass

    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")

    context = {
        "products": products,
        "products_by_category": products_by_category if group_by_category else None,
        "categories": categories,
        "cart": get_cart(request),
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "group_by_category": group_by_category,
        "related_posts": related_posts,
        "current_category": current_category,
        "navbar_items": navbar_items,
    }

    return render(request, "shop/product_list.html", context)


def product_detail(request, pk):
    """Display single product detail"""
    # Optimize product query with related data
    product = get_object_or_404(
        Product.objects.select_related("category", "supplier").prefetch_related(
            "images", "documents"
        ),
        pk=pk,
        status="active",
    )

    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")
    # Get product options with their items

    # Optimize product options query
    product_options = (
        ProductOption.objects.filter(product=product, is_active=True)
        .select_related("option_name")
        .prefetch_related("option_name__items")  # Prefetch related option items
    )

    # Build options data structure with items
    options_data = []
    for option in product_options:
        # Use prefetched items instead of separate query
        items = [item for item in option.option_name.items.all() if item.is_active]
        items.sort(key=lambda x: (x.ordering, x.value))

        options_data.append(
            {"option": option, "name": option.option_name.name, "items": items}
        )

    # Get related products from same category - optimize with select_related
    related_products = (
        Product.objects.filter(category=product.category, status="active")
        .select_related("category")
        .prefetch_related("images")
        .exclude(pk=product.pk)[:4]
    )

    # Get categories for sidebar - same as product_list view
    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("order", "name")
    )

    context = {
        "product": product,
        "related_products": related_products,
        "cart": get_cart(request),
        "product_options": options_data,
        "documents": product.documents.filter(is_public=True),
        "categories": categories,  # Add categories for sidebar
        "navbar_items": navbar_items,
    }

    return render(request, "shop/product_detail.html", context)


def cart_view(request):
    """Display shopping cart"""
    cart = get_cart(request)

    # Handle AJAX requests for cart items
    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.GET.get("format") == "json"
    ):

        cart_items_html = render_to_string("shop/cart_items.html", {"cart": cart})

        # Generate preview HTML for cart dropdown
        preview_html = ""
        if cart.items.exists():
            preview_html = '<div class="space-y-2">'
            for item in cart.items.all()[:3]:  # Show first 3 items
                # Get image URL
                image_html = '<div class="w-12 h-12 bg-base-300 rounded flex-shrink-0 overflow-hidden">'
                if item.product.main_image:
                    image_html = f'<div class="w-12 h-12 rounded flex-shrink-0 overflow-hidden"><img src="{item.product.main_image.url}" alt="" class="w-full h-full object-cover"></div>'
                elif item.product.images.exists():
                    first_image = item.product.images.first()
                    image_html = f'<div class="w-12 h-12 rounded flex-shrink-0 overflow-hidden"><img src="{first_image.image.url}" alt="" class="w-full h-full object-cover"></div>'
                else:
                    image_html += "</div>"

                preview_html += f"""
                <div class="flex items-center gap-3 p-2 hover:bg-base-200 rounded">
                    {image_html}
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium truncate">{item.product.name}</p>
                        <p class="text-xs text-base-content/60">Qty: {item.quantity} × ${item.product.price}</p>
                    </div>
                    <span class="text-sm font-semibold">${item.line_total}</span>
                </div>
                """
            if cart.items.count() > 3:
                preview_html += f'<p class="text-center text-sm text-base-content/60">... and {cart.items.count() - 3} more items</p>'
            preview_html += "</div>"
        else:
            preview_html = '<p class="text-center py-4 text-base-content/60">Your cart is empty</p>'

        return JsonResponse(
            {
                "html": cart_items_html,
                "subtotal": float(cart.subtotal),
                "total_items": cart.total_items,
                "preview_html": preview_html,
            }
        )

    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")
    # Get categories for sidebar
    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("order", "name")
    )

    return render(
        request,
        "shop/cart.html",
        {
            "cart": cart,
            "categories": categories,
            "navbar_items": navbar_items,
        },
    )


def add_to_cart(request, pk):
    """Add product to cart (AJAX)"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    product = get_object_or_404(Product, pk=pk, status="active")
    quantity = int(request.POST.get("quantity", 1))

    if quantity < 1:
        return JsonResponse({"error": "Invalid quantity"}, status=400)

    selected_options = {}
    options_json = request.POST.get("selected_options", "{}")
    try:
        selected_options = json.loads(options_json)
    except json.JSONDecodeError:
        pass

    # Validate that all required options are selected

    required_options = ProductOption.objects.filter(
        product=product, is_active=True
    ).select_related("option_name")

    for option in required_options:
        if option.option_name.name not in selected_options:
            return JsonResponse(
                {"error": f"Please select {option.option_name.name}"}, status=400
            )

    # Get or create cart
    cart = get_cart(request)

    # Try to find existing cart item with same product and options
    existing_item = None
    for item in cart.items.filter(product=product):
        if item.selected_options == selected_options:
            existing_item = item
            break

    if existing_item:
        # Update quantity if item with same options exists
        existing_item.quantity += quantity
        existing_item.save()
        cart_item = existing_item
    else:
        # Create new cart item
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            unit_price=product.price,
            selected_options=selected_options,
        )

    # Refresh cart from database to get updated items
    cart.refresh_from_db()

    # Alternatively, we can calculate directly from the database
    total_items = cart.items.aggregate(total=models.Sum("quantity"))["total"] or 0
    subtotal = sum(item.line_total for item in cart.items.all())

    return JsonResponse(
        {
            "success": True,
            "message": f"{product.name} added to cart",
            "cart_total_items": total_items,
            "cart_subtotal": float(subtotal),
        }
    )


def update_cart(request, pk):
    """Update cart item quantity (AJAX)"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    cart_item = get_object_or_404(CartItem, pk=pk)

    # Verify cart ownership
    if cart_item.cart.session_key != request.session.session_key:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    quantity = int(request.POST.get("quantity", 1))

    if quantity < 1:
        cart_item.delete()
        message = "Item removed from cart"
    else:
        cart_item.quantity = quantity
        cart_item.save()
        message = "Cart updated"

    cart = cart_item.cart

    return JsonResponse(
        {
            "success": True,
            "message": message,
            "cart_total_items": cart.total_items,
            "cart_subtotal": float(cart.subtotal),
            "item_total": float(cart_item.line_total) if quantity >= 1 else 0,
        }
    )


def remove_from_cart(request, pk):
    """Remove item from cart (AJAX)"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    cart_item = get_object_or_404(CartItem, pk=pk)

    # Verify cart ownership
    if cart_item.cart.session_key != request.session.session_key:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    cart = cart_item.cart
    cart_item.delete()

    return JsonResponse(
        {
            "success": True,
            "message": "Item removed from cart",
            "cart_total_items": cart.total_items,
            "cart_subtotal": float(cart.subtotal),
        }
    )


def checkout(request):
    """Checkout process"""
    cart = get_cart(request)

    if request.method == "GET":
        if not cart.items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect("shop:product_list")

        # Get shipping rates
        shipping_rates = ShippingRate.objects.filter(is_active=True)

        # Get saved addresses for authenticated users
        saved_addresses = None
        if request.user.is_authenticated:
            from customer.models import CustomerAddress

            saved_addresses = CustomerAddress.objects.filter(
                user=request.user, is_active=True
            ).order_by("-is_default", "-created_at")

        # Get categories for sidebar
        categories = Category.objects.filter(
            parent__isnull=True, is_active=True
        ).prefetch_related("children")

        navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")

        context = {
            "cart": cart,
            "shipping_rates": shipping_rates,
            "saved_addresses": saved_addresses,
            "categories": categories,
            "navbar_items": navbar_items,
        }

        return render(request, "shop/checkout.html", context)

    elif request.method == "POST":
        if not cart.items.exists():
            messages.error(request, "Your cart is empty")
            return redirect("shop:cart")

        try:
            # Check if we're using a saved address
            saved_address_id = request.POST.get("saved_address")
            if saved_address_id and request.user.is_authenticated:

                try:
                    address = CustomerAddress.objects.get(
                        pk=saved_address_id, user=request.user, is_active=True
                    )
                    # Use saved address data
                    first_name, last_name = (
                        address.recipient_name.split(" ", 1)
                        if " " in address.recipient_name
                        else (address.recipient_name, "")
                    )
                    billing_address_line1 = address.address_line1
                    billing_address_line2 = address.address_line2 or ""
                    billing_city = address.city
                    billing_state = address.state
                    billing_postal_code = address.postal_code
                    phone = address.phone or request.POST.get("phone", "")
                except CustomerAddress.DoesNotExist:
                    # Fallback to form data
                    first_name = request.POST.get("first_name")
                    last_name = request.POST.get("last_name")
                    billing_address_line1 = request.POST.get("address")
                    billing_address_line2 = request.POST.get("apartment", "")
                    billing_city = request.POST.get("city")
                    billing_state = request.POST.get("state")
                    billing_postal_code = request.POST.get("postal-code")
                    phone = request.POST.get("phone", "")
            else:
                # Use form data
                first_name = request.POST.get("first_name")
                last_name = request.POST.get("last_name")
                billing_address_line1 = request.POST.get("address")
                billing_address_line2 = request.POST.get("apartment", "")
                billing_city = request.POST.get("city")
                billing_state = request.POST.get("state")
                billing_postal_code = request.POST.get("postal-code")
                phone = request.POST.get("phone", "")

            # Get or create customer for authenticated users
            customer = None
            if request.user.is_authenticated:
                from customer.models import Customer

                try:
                    customer = request.user.customer
                except Customer.DoesNotExist:
                    # Create customer record for authenticated user if it doesn't exist
                    customer = Customer.objects.create(
                        user=request.user,
                        email=request.user.email,
                        first_name=first_name,
                        last_name=last_name,
                        phone=phone,
                    )

            # Create invoice (shop order)
            invoice = Invoice.objects.create(
                customer=customer,  # Link to customer if authenticated
                user=request.user if request.user.is_authenticated else None,
                is_shop_order=True,
                email=request.POST.get("email"),
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                billing_address_line1=billing_address_line1,
                billing_address_line2=billing_address_line2,
                billing_city=billing_city,
                billing_state=billing_state,
                billing_postal_code=billing_postal_code,
                billing_country="US",
                shipping_same_as_billing=True,  # For now, always use billing as shipping
                notes=request.POST.get("notes", ""),
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=30),
                status="sent",  # Shop orders start as sent
            )

            # Copy billing to shipping since we're using same address
            invoice.shipping_address_line1 = billing_address_line1
            invoice.shipping_address_line2 = billing_address_line2
            invoice.shipping_city = billing_city
            invoice.shipping_state = billing_state
            invoice.shipping_postal_code = billing_postal_code
            invoice.shipping_country = "US"

            # Add shipping cost (default to 0 for free shipping)
            shipping_rate_id = request.POST.get("shipping_rate")
            if shipping_rate_id:
                try:
                    shipping_rate = ShippingRate.objects.get(
                        pk=shipping_rate_id, is_active=True
                    )
                    cost = shipping_rate.calculate_cost(cart.subtotal, cart.total_items)
                    if cost is not None:
                        invoice.shipping_cost = cost
                except ShippingRate.DoesNotExist:
                    invoice.shipping_cost = Decimal("0")
            else:
                # No shipping rate selected, use free shipping
                invoice.shipping_cost = Decimal("0")

            # Apply promo code if provided
            promo_code = request.POST.get("promo_code")
            if promo_code:
                try:
                    promo = PromoCode.objects.get(code__iexact=promo_code)
                    if promo.is_valid():
                        invoice.discount_amount = promo.calculate_discount(
                            cart.subtotal
                        )
                        promo.used_count += 1
                        promo.save()
                except PromoCode.DoesNotExist:
                    pass

            invoice.save()

            # Create invoice items
            for cart_item in cart.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=cart_item.product,
                    description=cart_item.product.name,
                    product_options=cart_item.selected_options,  # Pass product options
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                )

            # Calculate totals
            invoice.calculate_totals()

            # Clear cart
            cart.clear()

            # Store order tracking code in session for anonymous users
            if not request.user.is_authenticated:
                request.session["last_order_tracking"] = str(invoice.tracking_code)

            # Add success message
            messages.success(
                request,
                f"Order #{invoice.invoice_number} has been placed successfully!",
            )

            # Redirect to order success page
            return redirect("shop:order_success", tracking_code=invoice.tracking_code)
        except Exception as e:
            # Log the error for debugging

            print(f"Checkout error: {str(e)}")
            print(traceback.format_exc())

            # Provide more specific error message
            error_msg = "An error occurred during checkout."
            if "email" in str(e).lower():
                error_msg = "Please provide a valid email address."
            elif "address" in str(e).lower() or "required" in str(e).lower():
                error_msg = "Please fill in all required fields."

            messages.error(request, f"{error_msg} Please try again.")
            return redirect("shop:checkout")


def order_success(request, tracking_code):
    """Order success page"""
    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")
    # Get categories for sidebar
    try:
        order = Invoice.objects.prefetch_related(
            "items",
            "items__product",
            "items__product__images",
        ).get(tracking_code=tracking_code, is_shop_order=True)
    except Invoice.DoesNotExist:
        order = None

    return render(
        request,
        "shop/order_success.html",
        {"order": order, "navbar_items": navbar_items},
    )


def order_tracking(request):
    """Track order by tracking code"""
    if request.method == "GET":
        return render(request, "shop/order_tracking.html")

    elif request.method == "POST":
        tracking_code = request.POST.get("tracking_code")
        email = request.POST.get("email")

        try:
            order = Invoice.objects.get(
                tracking_code=tracking_code, email__iexact=email, is_shop_order=True
            )
            return render(request, "shop/order_detail.html", {"order": order})
        except Invoice.DoesNotExist:
            messages.error(
                request, "Order not found. Please check your tracking code and email."
            )
            return render(request, "shop/order_tracking.html")


def blog_list(request):
    """Display list of published blog posts"""

    # Get only published posts
    posts = (
        Post.objects.filter(status="published")
        .select_related("author", "category")
        .prefetch_related("tags")
    )

    # Get blog categories for sidebar
    blog_categories = BlogCategory.objects.annotate(
        post_count=models.Count("posts", filter=models.Q(posts__status="published"))
    ).filter(post_count__gt=0)

    # Filter by category if provided
    category_slug = request.GET.get("category")
    if category_slug:
        posts = posts.filter(category__slug=category_slug)

    # Search functionality
    search_query = request.GET.get("search")
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query)
            | Q(excerpt__icontains=search_query)
            | Q(content__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(posts, 6)  # Show 6 posts per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("order", "name")
    )

    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")

    context = {
        "posts": page_obj,
        "blog_categories": blog_categories,
        "current_category": category_slug,
        "search_query": search_query,
        "categories": categories,
        "navbar_items": navbar_items,
    }

    return render(request, "shop/blog_list.html", context)


def blog_detail(request, pk):
    """Display single blog post detail"""

    # Get the post with related data
    post = get_object_or_404(
        Post.objects.select_related(
            "author", "category", "product_category"
        ).prefetch_related("tags", "related_products"),
        pk=pk,
        status="published",
    )

    # Increment view count
    post.views += 1
    post.save(update_fields=["views"])

    # Get related posts from same category
    related_posts = (
        Post.objects.filter(category=post.category, status="published")
        .exclude(pk=pk)
        .select_related("author", "category")[:3]
    )

    # Get recent posts for sidebar
    recent_posts = (
        Post.objects.filter(status="published")
        .exclude(pk=pk)
        .select_related("author", "category")[:5]
    )

    # Get blog categories for sidebar
    blog_categories = BlogCategory.objects.annotate(
        post_count=models.Count("posts", filter=models.Q(posts__status="published"))
    ).filter(post_count__gt=0)

    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")

    context = {
        "post": post,
        "related_posts": related_posts,
        "recent_posts": recent_posts,
        "blog_categories": blog_categories,
        "navbar_items": navbar_items,
    }

    return render(request, "shop/blog_detail.html", context)
