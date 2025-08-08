from django.urls import path
from . import views

app_name = 'customer_portal'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    
    # Addresses
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/add/', views.address_create, name='address_create'),
    path('addresses/<int:pk>/edit/', views.address_update, name='address_update'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
    path('addresses/<int:pk>/set-default/', views.set_default_address, name='address_set_default'),
    
    # Password
    path('change-password/', views.change_password, name='change_password'),
    
    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:pk>/mark-read/', views.mark_notification_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='notification_mark_all_read'),
    path('notifications/count/', views.get_notification_count, name='notification_count'),
]