from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.PostListView.as_view(), name='post-list'),
    path('post/new/', views.PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('post/<int:pk>/edit/', views.PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post-delete'),
    path('post/<int:pk>/publish/', views.publish_post, name='post-publish'),
    path('post/<int:pk>/like/', views.like_post, name='like-post'),
    path('post/<int:pk>/comment/', views.add_comment, name='add-comment'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('tag/<slug:slug>/', views.TagDetailView.as_view(), name='tag-detail'),
    path('author/<str:username>/', views.UserPostListView.as_view(), name='user-posts'),
]