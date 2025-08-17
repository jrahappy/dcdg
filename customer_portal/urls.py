from django.urls import path
from . import views

app_name = "customer_portal"

urlpatterns = [
    # Test view for debugging
    path("test/", views.test_view, name="test"),
    # Dashboard
    path("manage/dashboard/", views.dashboard, name="dashboard"),
    # Orders
    path("manage/orders/", views.order_list, name="order_list"),
    path("manage/orders/<int:pk>/", views.order_detail, name="order_detail"),
    # Profile
    path("manage/profile/", views.profile_view, name="profile"),
    path("manage/profile/edit/", views.profile_edit, name="profile_edit"),
    path("manage/profile/upload-image/", views.profile_image_upload, name="profile_image_upload"),
    # Company Information
    path("manage/company/", views.company_info, name="company_info"),
    path("manage/company/edit/", views.company_info_edit, name="company_info_edit"),
    # Addresses
    path("manage/addresses/", views.address_list, name="address_list"),
    path("manage/addresses/add/", views.address_create, name="address_create"),
    path(
        "manage/addresses/<int:pk>/edit/", views.address_update, name="address_update"
    ),
    path(
        "manage/addresses/<int:pk>/delete/", views.address_delete, name="address_delete"
    ),
    path(
        "manage/addresses/<int:pk>/set-default/",
        views.set_default_address,
        name="address_set_default",
    ),
    # Password
    path("manage/change-password/", views.change_password, name="change_password"),
    # Notifications
    path("manage/notifications/", views.notification_list, name="notification_list"),
    path(
        "manage/notifications/<int:pk>/",
        views.notification_detail,
        name="notification_detail",
    ),
    path(
        "manage/notifications/<int:pk>/mark-read/",
        views.mark_notification_read,
        name="notification_mark_read",
    ),
    path(
        "manage/notifications/mark-all-read/",
        views.mark_all_notifications_read,
        name="notification_mark_all_read",
    ),
    path(
        "manage/notifications/count/",
        views.get_notification_count,
        name="notification_count",
    ),
]
