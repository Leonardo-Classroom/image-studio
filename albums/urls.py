from django.urls import path

from . import views

urlpatterns = [
    path("albums/", views.album_list, name="album_list"),
    path("albums/new/", views.album_new, name="album_new"),
    path("albums/analyze/", views.album_analyze, name="album_analyze"),
    path("albums/<int:pk>/setup/", views.album_setup, name="album_setup"),
    path("albums/<int:pk>/create/", views.album_create, name="album_create"),
    path("albums/<int:pk>/", views.album_detail, name="album_detail"),
    path("albums/<int:pk>/progress/", views.album_progress, name="album_progress"),
    path("albums/<int:pk>/discard/", views.album_discard_draft, name="album_discard_draft"),
    path("albums/item/<int:pk>/source-thumb/", views.item_source_thumb, name="item_source_thumb"),
]
