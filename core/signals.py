import os
import shutil
import django_rq
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Video
from .tasks import convert_to_hls
from .utils import get_hls_output_path


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    if created:
        queue = django_rq.get_queue('default')
        source = instance.video_file.path
        queue.enqueue(convert_to_hls, instance.pk, source, '480p', 480)
        queue.enqueue(convert_to_hls, instance.pk, source, '720p', 720)
        queue.enqueue(convert_to_hls, instance.pk, source, '1080p', 1080)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance, **kwargs):
    if instance.video_file and os.path.isfile(instance.video_file.path):
        os.remove(instance.video_file.path)
    if instance.thumbnail and os.path.isfile(instance.thumbnail.path):
        os.remove(instance.thumbnail.path)
    video_dir = os.path.dirname(get_hls_output_path(instance.pk, ''))
    if os.path.isdir(video_dir):
        shutil.rmtree(video_dir, ignore_errors=True)
