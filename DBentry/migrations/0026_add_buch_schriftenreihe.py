# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-18 09:46
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0025_add_model_schriftenreihe'),
    ]

    operations = [
        migrations.AddField(
            model_name='buch',
            name='schriftenreihe',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.schriftenreihe'),
        ),
    ]
