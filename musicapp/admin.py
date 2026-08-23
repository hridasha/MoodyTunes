from django.contrib import admin
from .models import *
# Register your models here.


@admin.action(description='Approve selected songs')
def approve_songs(modeladmin, request, queryset):
    queryset.update(status='Approved')


@admin.action(description='Reject selected songs')
def reject_songs(modeladmin, request, queryset):
    queryset.update(status='Rejected')


class SongAdmin(admin.ModelAdmin):
    list_display = ('name', 'artist', 'mood', 'language', 'status', 'uploaded_by')
    list_filter = ('status', 'mood', 'language')
    actions = [approve_songs, reject_songs]


admin.site.register(Song, SongAdmin)
admin.site.register(Playlist)
admin.site.register(Favourite)
admin.site.register(Recent)
admin.site.register(Rating)
