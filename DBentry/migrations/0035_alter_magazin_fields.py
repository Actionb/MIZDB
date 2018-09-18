# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-18 10:46
from __future__ import unicode_literals

import DBentry.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0034_alter_magazin_erstausgabe'),
    ]

    operations = [
        migrations.AlterField(
            model_name='magazin',
            name='fanzine',
            field=models.BooleanField(default=False, verbose_name='Fanzine'),
        ),
        migrations.AlterField(
            model_name='magazin',
            name='issn',
            field=DBentry.fields.ISSNField(blank=True, max_length=9, verbose_name='ISSN'),
        ),
        migrations.AlterField(
            model_name='magazin',
            name='ort',
            field=models.ForeignKey(blank=True, help_text='Angabe für auf eine Region beschränktes Magazin.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.ort', verbose_name='Hrsg.Ort'),
        ),
    ]
