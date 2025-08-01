from django.urls import path, re_path
from . import views

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile-edit'),
    
    # Account Management URLs
    path('manage/', views.account_profile, name='account-profile'),
    path('manage/profile/', views.account_profile, name='account-profile'),
    path('manage/info/', views.account_info, name='account-info'),
    path('manage/security/', views.account_security, name='account-security'),
    
    # Logout confirmation
    path('logout/', views.logout_confirm, name='logout-confirm'),
    
    # Override allauth email confirmation URLs
    path('confirm-email/', views.redirect_email_confirm, name='account_email_verification_sent'),
    re_path(r'^confirm-email/(?P<key>[-:\w]+)/$', views.redirect_email_confirm, name='account_confirm_email'),
    # Catch any other email-related URLs
    re_path(r'^.*email.*/$', views.redirect_email_confirm),
    re_path(r'^.*confirm.*/$', views.redirect_email_confirm),
]