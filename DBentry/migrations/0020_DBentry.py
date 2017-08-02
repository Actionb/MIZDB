# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-24 10:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0019_DBentry'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bundesland',
            options={'ordering': ['land', 'bland_name'], 'verbose_name': 'Bundesland', 'verbose_name_plural': 'Bundesländer'},
        ),
        migrations.AlterModelOptions(
            name='land',
            options={'ordering': ['land_name'], 'verbose_name': 'Land', 'verbose_name_plural': 'Länder'},
        ),
        migrations.AlterField(
            model_name='bundesland',
            name='code',
            field=models.CharField(max_length=4),
        ),
    ]
