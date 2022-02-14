from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Watchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.IntegerField()
    object_repr = models.CharField(max_length=200)
    added = models.DateTimeField(auto_now_add=True)  # TODO: rename to time_added
    # TODO: add 'notes' model field?

    def __str__(self):
        return self.object_repr

    class Meta:
        ordering = ['user', 'content_type', 'added']
        verbose_name = 'Merkliste'
        verbose_name_plural = 'Merklisten'
