"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include("shop.urls")),  # Landing page is now the homepage
    path("landing/", include("landing.urls")),  # Landing page is now the homepage
    path("home/", include("dashboard.urls")),  # Dashboard for logged-in users
    path("home/customer/", include("customer.urls")),  # Customer addresses
    path("home/email-campaign/", include("email_campaign.urls")),  # Email campaigns
    path("home/email-templates/", include("email_templates.urls")),  # Email templates
    path("home/products/", include("product.urls")),  # Product management
    path("home/purchases/", include("purchases.urls")),  # Purchase orders
    path("home/sales/", include("sales.urls")),  # Sales app (quotes, orders, invoices)
    path("home/blog/", include("blog.urls")),  # Blog moved to /blog/
    path("shop/", include("shop.urls")),  # Shop for anonymous visitors
    path(
        "account/", include("customer_portal.urls")
    ),  # Customer portal for logged-in shoppers
    path("account/chat/", include("chat.urls")),  # Chat support for customers
    path("factory/", include("factory_portal.urls")),  # Factory portal for suppliers
    path("admin/", admin.site.urls),
    path("summernote/", include("django_summernote.urls")),
    # Load accounts URLs first to override allauth's email confirmation
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("dogfoot/", include("dogfoot.urls")),  # Dogfooding app
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
