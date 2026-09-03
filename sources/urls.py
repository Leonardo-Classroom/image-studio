from django.urls import path

from . import views

urlpatterns = [
    path("sources/browse/", views.browse, name="source_browse"),
    path("sources/thumb/<int:root_id>/", views.thumb, name="source_thumb"),
]
