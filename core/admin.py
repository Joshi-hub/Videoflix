from django.contrib import admin
from .models import Genre, Video


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'genre', 'created_at']
    list_filter = ['genre']
