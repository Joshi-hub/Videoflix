from django.urls import path
from .views import VideoListView, HLSManifestView, HLSSegmentView

urlpatterns = [
    path('', VideoListView.as_view(), name='video-list'),
    path('<int:movie_id>/<str:resolution>/index.m3u8', HLSManifestView.as_view(), name='hls-manifest'),
    path('<int:movie_id>/<str:resolution>/<str:segment>/', HLSSegmentView.as_view(), name='hls-segment'),
]
