from django.shortcuts import render
from product.models import Product, Category
from pages.models import NavMenu


# Create your views here.
def support(request):

    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")

    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("order", "name")
    )

    cbct_products = Product.objects.filter(status="active")[:4]

    print("CBCT Products:", cbct_products)

    context = {
        "categories": categories,
        "navbar_items": navbar_items,
        "cbct_products": cbct_products,
    }
    return render(request, "pages/support.html", context)


def home(request):

    navbar_items = NavMenu.objects.filter(is_active=True).order_by("order")

    categories = (
        Category.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("order", "name")
    )
    cbct_products = (
        Product.objects.filter(status="active", tags__contains="cbct")
        .select_related("category")
        .order_by("-created_at")[:4]
    )
    od_products = (
        Product.objects.filter(status="active", category=12)
        .select_related("category")
        .order_by("-created_at")[:8]
    )
    context = {
        "categories": categories,
        "navbar_items": navbar_items,
        "cbct_products": cbct_products,
        "od_products": od_products,
    }

    return render(request, "pages/home.html", context)
