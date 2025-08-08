from django.urls import path
from . import views, periodic_views

app_name = 'email_campaign'

urlpatterns = [
    path('', views.campaign_list, name='campaign_list'),
    path('customer-selection/', views.customer_selection, name='customer_selection'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('target-group-cart/', views.target_group_cart_view, name='target_group_cart'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    # Legacy campaign creation (keep for existing links)
    path('campaign/create/', views.campaign_create, name='campaign_create'),
    path('campaign/create/<int:target_group_id>/', views.campaign_create, name='campaign_create_with_group'),
    
    # New 3-step campaign creation
    path('campaign/new/step1/', views.campaign_create_step1, name='campaign_create_step1'),
    path('campaign/new/step2/', views.campaign_create_step2, name='campaign_create_step2'),
    path('campaign/new/step3/', views.campaign_create_step3, name='campaign_create_step3'),
    path('campaign/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaign/<int:pk>/send/', views.send_campaign, name='send_campaign'),
    path('campaign/<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),
    
    # Target Group URLs
    path('target-groups/', views.target_group_list, name='target_group_list'),
    path('target-groups/<int:pk>/', views.target_group_detail, name='target_group_detail'),
    path('target-groups/<int:pk>/edit/', views.target_group_edit, name='target_group_edit'),
    path('target-groups/<int:pk>/delete/', views.target_group_delete, name='target_group_delete'),
    
    # Periodic Campaign URLs
    path('periodic/', periodic_views.periodic_campaign_list, name='periodic_campaign_list'),
    path('periodic/create/', periodic_views.periodic_campaign_create, name='periodic_campaign_create'),
    path('periodic/<int:pk>/', periodic_views.periodic_campaign_detail, name='periodic_campaign_detail'),
    path('periodic/<int:pk>/edit/', periodic_views.periodic_campaign_edit, name='periodic_campaign_edit'),
    path('periodic/<int:pk>/delete/', periodic_views.periodic_campaign_delete, name='periodic_campaign_delete'),
    path('periodic/<int:pk>/logs/', periodic_views.periodic_campaign_logs, name='periodic_campaign_logs'),
    path('periodic/<int:pk>/toggle-status/', periodic_views.periodic_campaign_toggle_status, name='periodic_campaign_toggle_status'),
    path('periodic/<int:pk>/test-run/', periodic_views.periodic_campaign_test_run, name='periodic_campaign_test_run'),
]