from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_list, name='chat_list'),
    path('create/', views.create_chat, name='create_chat'),
    path('<int:pk>/', views.chat_room, name='chat_room'),
    path('<int:pk>/close/', views.close_chat, name='close_chat'),
    path('<int:pk>/new-messages/', views.get_new_messages, name='get_new_messages'),
    path('unread-count/', views.get_unread_count, name='get_unread_count'),
]