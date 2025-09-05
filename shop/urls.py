from django.urls import path
from . import views

app_name = "shop"

urlpatterns = [
    # Product browsing
    path("", views.index, name="index"),
    path("products/", views.product_list, name="product_list"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    # Cart management
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:pk>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:pk>/", views.remove_from_cart, name="remove_from_cart"),
    # Checkout
    path("checkout/", views.checkout, name="checkout"),
    # Order management
    path(
        "order/success/<uuid:tracking_code>/", views.order_success, name="order_success"
    ),
    path("order/track/", views.order_tracking, name="order_tracking"),
    # Blog
    path("blog/", views.blog_list, name="blog_list"),
    path("blog/<int:pk>/", views.blog_detail, name="blog_detail"),
]
