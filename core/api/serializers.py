from rest_framework import serializers
from core.models import Genre, Video


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['id', 'title', 'description', 'thumbnail', 'created_at']


class GenreSerializer(serializers.ModelSerializer):
    videos = VideoSerializer(many=True, read_only=True)

    class Meta:
        model = Genre
        fields = ['id', 'name', 'videos']
