# Generated by Django 2.2.16 on 2021-03-08 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0019_add_audio_land_pressung'),
    ]

    operations = [
        migrations.AddField(
            model_name='ausgabe',
            name='video',
            field=models.ManyToManyField(to='dbentry.Video'),
        ),
    ]