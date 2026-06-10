from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from core.models import Genre
from .serializers import GenreSerializer


class VideoListView(ListAPIView):
    queryset = Genre.objects.prefetch_related('videos').all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticated]
