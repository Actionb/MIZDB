# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-18 09:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0026_add_buch_schriftenreihe'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Organisation',
                'verbose_name_plural': 'Organisationen',
            },
        ),
    ]
