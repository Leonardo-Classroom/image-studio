from django.urls import path

from . import views

urlpatterns = [
    path("text/", views.text_list, name="text_list"),
    path("text/create/", views.text_create, name="text_create"),
    path("text/<int:pk>/", views.text_detail, name="text_detail"),
    path("text/<int:pk>/status/", views.text_status, name="text_status"),
    path("text/<int:pk>/regenerate/", views.text_regenerate, name="text_regenerate"),
    path("jobs/<int:pk>/retry/", views.job_retry, name="job_retry"),
]
