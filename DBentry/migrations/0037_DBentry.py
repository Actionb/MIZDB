# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-20 11:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0036_DBentry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='geber',
            name='name',
            field=models.CharField(default='unbekannt', max_length=100),
        ),
    ]
