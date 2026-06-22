import os
from django.conf import settings


def get_hls_output_path(video_id, resolution):
    """Returns the filesystem path to the HLS output directory for a given video and resolution."""
    return os.path.join(settings.MEDIA_ROOT, 'videos', str(video_id), resolution)
