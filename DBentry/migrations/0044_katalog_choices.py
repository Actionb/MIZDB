# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-03-11 09:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0043_magazin_verlag_adds_explicit_m2m_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='katalog',
            name='art',
            field=models.CharField(choices=[('merch', 'Merchandise'), ('tech', 'Instrumente & Technik'), ('ton', 'Tonträger'), ('buch', 'Bücher'), ('other', 'Anderes')], default=1, max_length=40, verbose_name='Art d. Kataloges'),
        ),
    ]
