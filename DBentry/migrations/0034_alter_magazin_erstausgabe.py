# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-18 10:19
from __future__ import unicode_literals

from django.db import migrations, models

# Alter magazin.erstausgabe from a DateField to a CharField

class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0033_remove_magazin_verlag_foreignkey'),
    ]

    operations = [
        migrations.AlterField(
            model_name='magazin',
            name='erstausgabe',
            field=models.CharField(blank=True, default='', max_length=200),
            preserve_default=False,
        ),
    ]