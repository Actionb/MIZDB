# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-19 09:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ausgabe',
            name='_changed_flag',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AddField(
            model_name='ausgabe',
            name='_name',
            field=models.CharField(default='No data for %(verbose_name)s.', editable=False, max_length=200),
        ),
    ]
