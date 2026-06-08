from django.db.models.signals import post_save, post_delete
from .models import Video
from .tasks import convert_480p_video
from django.dispatch import receiver
import os


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    print('video wurde gespeichert')
    if created:
        print('new video wurde gespeichert')
        convert_480p_video.delay(instance.video_file.path)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance, **kwargs):
    print('video wurde gelöscht')
    if instance.video_file:
        if os.path.isfile(instance.video_file.path): 
            os.remove(instance.video_file.path)
            print('video file wurde gelöscht')
    if instance.thumbnail:
        if os.path.isfile(instance.thumbnail.path):
            os.remove(instance.thumbnail.path)  
            print('thumbnail wurde gelöscht')




       