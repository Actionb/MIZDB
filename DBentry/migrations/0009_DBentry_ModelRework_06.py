# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-11 10:35
from __future__ import unicode_literals

import DBentry.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0008_DBentry_ModelRework_05'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datei',
            name='datum',
        ),
        migrations.AlterField(
            model_name='genre',
            name='ober',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sub_genres', to='DBentry.genre', verbose_name='Oberbegriff'),
        ),
        migrations.AlterField(
            model_name='magazin',
            name='issn',
            field=DBentry.fields.ISSNField(blank=True, max_length=9),
        ),
        migrations.AlterField(
            model_name='schlagwort',
            name='ober',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='unterbegriffe', to='DBentry.schlagwort', verbose_name='Oberbegriff'),
        ),
    ]