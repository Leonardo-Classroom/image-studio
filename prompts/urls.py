from django.urls import path

from . import views

urlpatterns = [
    path("prompts/", views.prompt_list, name="prompt_list"),
    path("prompts/save/", views.prompt_save, name="prompt_create"),
    path("prompts/<int:pk>/save/", views.prompt_save, name="prompt_edit"),
    path("prompts/<int:pk>/delete/", views.prompt_delete, name="prompt_delete"),
]
