import os
from django.conf import settings


def get_hls_output_path(video_id, resolution):
    return os.path.join(settings.MEDIA_ROOT, 'videos', str(video_id), resolution)
