# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-03 08:18
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0015_DBentry_ModelRework_12_OrteFKRemoved'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='autor',
            name='orte',
        ),
    ]
