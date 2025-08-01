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
    path("", include("landing.urls")),  # Landing page is now the homepage
    path("dashboard/", include("dashboard.urls")),  # Dashboard for logged-in users
    path(
        "dashboard/email-campaign/", include("email_campaign.urls")
    ),  # Email campaigns
    path("blog/", include("blog.urls")),  # Blog moved to /blog/
    path("admin/", admin.site.urls),
    path("summernote/", include("django_summernote.urls")),
    # Load accounts URLs first to override allauth's email confirmation
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("dogfoot/", include("dogfoot.urls")),  # Dogfooding app
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
