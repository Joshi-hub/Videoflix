from rest_framework import serializers
from videos.models import Video


class VideoSerializer(serializers.ModelSerializer):
    """Serializes a Video with an absolute thumbnail URL and the genre name as category."""

    thumbnail_url = serializers.ImageField(source='thumbnail', use_url=True)
    category = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'created_at', 'title', 'description', 'thumbnail_url', 'category']

    def get_category(self, obj):
        """Returns the genre name or None if no genre is assigned."""
        return obj.genre.name if obj.genre else None
