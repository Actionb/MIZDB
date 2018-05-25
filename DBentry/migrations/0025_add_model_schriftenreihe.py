# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-18 09:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0024_remove_model_buchserie'),
    ]

    operations = [
        migrations.CreateModel(
            name='schriftenreihe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
            ],
            options={
                'verbose_name_plural': 'Schriftenreihen',
                'abstract': False,
                'default_permissions': ('add', 'change', 'delete', 'merge'),
                'verbose_name': 'Schriftenreihe',
                'ordering': ['name'],
            },
        ),
    ]