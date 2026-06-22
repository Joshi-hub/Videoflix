import os
import subprocess
from .utils import get_hls_output_path


def _build_ffmpeg_cmd(source_path, scale, output_m3u8, segment_pattern):
    """Builds the ffmpeg argument list for HLS encoding at the given scale."""
    return [
        'ffmpeg', '-i', source_path,
        '-vf', f'scale=-2:{scale}',
        '-codec:v', 'libx264', '-codec:a', 'aac',
        '-hls_time', '10', '-hls_playlist_type', 'vod',
        '-hls_segment_filename', segment_pattern,
        output_m3u8,
    ]


def convert_to_hls(video_id, source_path, resolution, scale):
    """Converts a video to HLS segments at the given resolution via ffmpeg."""
    output_dir = get_hls_output_path(video_id, resolution)
    os.makedirs(output_dir, exist_ok=True)
    output_m3u8 = os.path.join(output_dir, 'index.m3u8')
    segment_pattern = os.path.join(output_dir, '%03d.ts')
    cmd = _build_ffmpeg_cmd(source_path, scale, output_m3u8, segment_pattern)
    subprocess.run(cmd, check=True)
