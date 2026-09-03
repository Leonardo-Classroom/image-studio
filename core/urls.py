from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("settings/", views.settings_page, name="settings"),
    path("settings/datasets/add/", views.dataset_root_add, name="dataset_root_add"),
    path("settings/datasets/<int:pk>/delete/", views.dataset_root_delete, name="dataset_root_delete"),
]
