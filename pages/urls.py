from django.urls import path
from . import views

app_name = "pages"
urlpatterns = [
    path("support/", views.support, name="support"),
    path("", views.home, name="home"),
]
