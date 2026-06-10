from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Video(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, related_name='videos')
    video_file = models.FileField(upload_to='videos/originals/')
    thumbnail = models.ImageField(upload_to='videos/thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
