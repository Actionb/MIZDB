# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-10-24 09:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0036_alter_fields_laufzeit_audio_and_video'),
    ]

    operations = [
        migrations.AlterField(
            model_name='verlag',
            name='verlag_name',
            field=models.CharField(max_length=200, verbose_name='Verlag'),
        ),
    ]