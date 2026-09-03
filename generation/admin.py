from django.contrib import admin

from .models import GeneratedImage, GenerationJob, TextSession

admin.site.register(TextSession)
admin.site.register(GeneratedImage)
admin.site.register(GenerationJob)
