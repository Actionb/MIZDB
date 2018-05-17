# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-17 06:54
from __future__ import unicode_literals

from django.db import migrations, models

def forwards(apps, schema_editor):
    monat = apps.get_model('DBentry', 'monat')
    order = ['Jan', 'Feb', 'Mrz', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
    for id, abk in monat.objects.values_list('pk', 'abk'):
        monat.objects.filter(pk=id).update(ordinal=order.index(abk)+1)


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0021_alter_ausgabe_jahrgang'),
    ]

    operations = [
        migrations.AddField(
            model_name='monat',
            name='ordinal',
            field=models.PositiveSmallIntegerField(default=1, editable=False),
            preserve_default=False,
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop), 
        migrations.AlterModelOptions(
            name='monat',
            options={'default_permissions': ('add', 'change', 'delete', 'merge'), 'ordering': ['ordinal'], 'verbose_name': 'Monat', 'verbose_name_plural': 'Monate'},
        ),
    ]
