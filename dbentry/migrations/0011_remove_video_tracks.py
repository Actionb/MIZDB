# Generated by Django 2.2.16 on 2020-10-22 11:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0010_remove_bestand_bestand_art'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='video',
            name='tracks',
        ),
    ]
