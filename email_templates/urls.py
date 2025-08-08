from django.urls import path
from . import views

app_name = 'email_templates'

urlpatterns = [
    path('', views.template_list, name='template_list'),
    # Legacy single-step creation (keep for backward compatibility)
    path('create/', views.template_create, name='template_create_legacy'),
    # New 2-step creation process
    path('create/step1/', views.template_create_step1, name='template_create'),
    path('create/step2/', views.template_create_step2, name='template_create_step2'),
    path('<int:pk>/', views.template_detail, name='template_detail'),
    path('<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('<int:pk>/duplicate/', views.template_duplicate, name='template_duplicate'),
    path('<int:pk>/preview/', views.template_preview, name='template_preview'),
    path('api/variables/', views.template_variables, name='template_variables'),
    
    # Variable CRUD URLs
    path('<int:template_pk>/variables/', views.variable_list, name='variable_list'),
    path('<int:template_pk>/variables/create/', views.variable_create, name='variable_create'),
    path('<int:template_pk>/variables/<int:variable_pk>/update/', views.variable_update, name='variable_update'),
    path('<int:template_pk>/variables/<int:variable_pk>/delete/', views.variable_delete, name='variable_delete'),
]