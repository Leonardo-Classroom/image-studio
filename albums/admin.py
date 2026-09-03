from django.contrib import admin

from .models import Album, AlbumItem, Folder, Tag, TagOccurrence

admin.site.register(Folder)
admin.site.register(Album)
admin.site.register(AlbumItem)
admin.site.register(Tag)
admin.site.register(TagOccurrence)
