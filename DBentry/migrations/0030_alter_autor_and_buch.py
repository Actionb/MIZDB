# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-09-18 09:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0029_add_buch_herausgeber'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ausgabe',
            options={'default_permissions': ('add', 'change', 'delete', 'merge'), 'ordering': ['magazin'], 'permissions': [('alter_bestand_ausgabe', 'Aktion: Bestand/Dublette hinzufügen.'), ('alter_data_ausgabe', 'Aktion: Daten verändern.')], 'verbose_name': 'Ausgabe', 'verbose_name_plural': 'Ausgaben'},
        ),
        migrations.AlterModelOptions(
            name='ausgabe_monat',
            options={'default_permissions': ('add', 'change', 'delete', 'merge'), 'ordering': ['monat'], 'verbose_name': 'Ausgabe-Monat', 'verbose_name_plural': 'Ausgabe-Monate'},
        ),
        migrations.AlterField(
            model_name='autor',
            name='person',
            field=models.ForeignKey(blank=True, help_text='Zur Schnell-Erstellung bitte folgendes Format benutzen: Nachname(n), Vorname(n)', null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.person'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='autor',
            field=models.ManyToManyField(help_text='Zur Schnell-Erstellung bitte folgendes Format benutzen: Nachname(n), Vorname(n) (Kürzel)', to='DBentry.autor'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='buchband',
            field=models.ForeignKey(blank=True, help_text='Der Sammelband, der diesen Aufsatz enthält.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='buch_set', to='DBentry.buch', verbose_name='Sammelband'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='is_buchband',
            field=models.BooleanField(default=False, help_text='Dieses Buch ist ein Sammelband bestehend aus Aufsätzen.', verbose_name='Ist Sammelband'),
        ),
    ]