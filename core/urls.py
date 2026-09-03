from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("settings/", views.settings_page, name="settings"),
    path("settings/app/", views.app_setting_save, name="app_setting_save"),
    path("settings/datasets/add/", views.dataset_root_add, name="dataset_root_add"),
    path("settings/datasets/<int:pk>/delete/", views.dataset_root_delete, name="dataset_root_delete"),
    path("services/", views.services_page, name="services"),
    path("services/status/", views.services_status, name="services_status"),
    path("services/<str:name>/start/", views.service_start, name="service_start"),
    path("services/<str:name>/stop/", views.service_stop, name="service_stop"),
    path("favorites/", views.favorites, name="favorites"),
    path("trash/", views.trash, name="trash"),
    path("trash/<str:kind>/<int:pk>/restore/", views.trash_restore, name="trash_restore"),
    path("trash/<str:kind>/<int:pk>/purge/", views.trash_purge, name="trash_purge"),
]
