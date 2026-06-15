from rest_framework import serializers
from core.models import Video


class VideoSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.ImageField(source='thumbnail', use_url=True)
    category = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'created_at', 'title', 'description', 'thumbnail_url', 'category']

    def get_category(self, obj):
        return obj.genre.name if obj.genre else None
