# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-11-09 10:08
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0038_adds_brochure_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrochureURL',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(blank=True, verbose_name='Webpage')),
                ('brochure', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='urls', to='DBentry.BaseBrochure')),
            ],
            options={
                'abstract': False,
                'default_permissions': ('add', 'change', 'delete', 'merge'),
                'verbose_name': 'Web-Adresse',
                'verbose_name_plural': 'Web-Adressen',
            },
        ),
    ]