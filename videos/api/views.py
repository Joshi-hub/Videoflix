import os
import re
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from videos.models import Video
from videos.utils import get_hls_output_path
from .serializers import VideoSerializer

_ALLOWED_RESOLUTIONS = {'480p', '720p', '1080p'}
_SEGMENT_RE = re.compile(r'^\d{3}\.ts$')


class VideoListView(ListAPIView):
    """Returns a list of all videos ordered by creation date descending."""

    queryset = Video.objects.select_related('genre').all()
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]


class HLSManifestView(APIView):
    """Serves the HLS m3u8 playlist file for a given video and resolution."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        if resolution not in _ALLOWED_RESOLUTIONS:
            raise Http404
        get_object_or_404(Video, pk=movie_id)
        manifest_path = os.path.join(get_hls_output_path(movie_id, resolution), 'index.m3u8')
        if not os.path.isfile(manifest_path):
            raise Http404
        return FileResponse(open(manifest_path, 'rb'), content_type='application/vnd.apple.mpegurl')


class HLSSegmentView(APIView):
    """Serves a single .ts segment file for a given video and resolution."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        if resolution not in _ALLOWED_RESOLUTIONS or not _SEGMENT_RE.match(segment):
            raise Http404
        get_object_or_404(Video, pk=movie_id)
        segment_path = os.path.join(get_hls_output_path(movie_id, resolution), segment)
        if not os.path.isfile(segment_path):
            raise Http404
        return FileResponse(open(segment_path, 'rb'), content_type='video/MP2T')
