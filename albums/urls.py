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
    path("albums/<int:pk>/view/", views.album_view, name="album_view"),
    path("albums/item/<int:pk>/view/", views.item_view, name="item_view"),
    path("albums/item/<int:pk>/caption/", views.item_caption, name="item_caption"),
    path("albums/item/<int:pk>/generate/", views.item_generate, name="item_generate"),
    path("albums/tag/<int:pk>/toggle/", views.tag_toggle, name="tag_toggle"),
    path("favorites/<int:pk>/toggle/", views.favorite_toggle, name="favorite_toggle"),
]
