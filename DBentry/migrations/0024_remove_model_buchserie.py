# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-18 09:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0023_model_buch_fields'),
    ]

    operations = [
        migrations.DeleteModel(
            name='buch_serie',
        ),
    ]
