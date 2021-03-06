# Generated by Django 2.2.16 on 2020-10-28 13:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0013_audio_video_original_helptext'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='discogs_url',
            field=models.URLField(blank=True, help_text='Adresse zur discogs.com Seite dieses Objektes.', verbose_name='Link discogs.com'),
        ),
        migrations.AddField(
            model_name='video',
            name='release_id',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Release ID (discogs)'),
        ),
    ]
