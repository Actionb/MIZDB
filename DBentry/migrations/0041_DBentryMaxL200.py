# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-22 09:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0040_DBentry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='artikel',
            name='schlagzeile',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='audio',
            name='festplatte',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='audio',
            name='quelle',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='audio',
            name='titel',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='autor',
            name='kuerzel',
            field=models.CharField(blank=True, max_length=200, verbose_name='Kürzel'),
        ),
        migrations.AlterField(
            model_name='band',
            name='band_name',
            field=models.CharField(max_length=200, verbose_name='Bandname'),
        ),
        migrations.AlterField(
            model_name='bildmaterial',
            name='titel',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='buch',
            name='EAN',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='buch',
            name='ISBN',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='buch',
            name='LCCN',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='buch',
            name='auflage',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='buch',
            name='ausgabe',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='buch',
            name='buch_band',
            field=models.CharField(blank=True, max_length=200, verbose_name='Buch Band'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='titel',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='buch',
            name='titel_orig',
            field=models.CharField(blank=True, max_length=200, verbose_name='Titel (Original)'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='ubersetzer',
            field=models.CharField(blank=True, max_length=200, verbose_name='Übersetzer'),
        ),
        migrations.AlterField(
            model_name='buch_serie',
            name='serie',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='bundesland',
            name='bland_name',
            field=models.CharField(max_length=200, verbose_name='Bundesland'),
        ),
        migrations.AlterField(
            model_name='dokument',
            name='titel',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='geber',
            name='name',
            field=models.CharField(default='unbekannt', max_length=200),
        ),
        migrations.AlterField(
            model_name='instrument',
            name='instrument',
            field=models.CharField(max_length=200, unique=True),
        ),
        migrations.AlterField(
            model_name='instrument',
            name='kuerzel',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='kreis',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='lagerort',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='lagerort',
            name='signatur',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='magazin',
            name='beschreibung',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='magazin',
            name='magazin_name',
            field=models.CharField(max_length=200, verbose_name='Magazin'),
        ),
        migrations.AlterField(
            model_name='magazin',
            name='turnus',
            field=models.CharField(blank=True, choices=[('u', 'unbekannt'), ('t', 'täglich'), ('w', 'wöchentlich'), ('w2', 'zwei-wöchentlich'), ('m', 'monatlich'), ('m2', 'zwei-monatlich'), ('q', 'quartalsweise'), ('hj', 'halbjährlich'), ('j', 'jährlich')], default='m', max_length=200),
        ),
        migrations.AlterField(
            model_name='memorabilien',
            name='titel',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='monat',
            name='abk',
            field=models.CharField(max_length=200, verbose_name='Abk'),
        ),
        migrations.AlterField(
            model_name='monat',
            name='monat',
            field=models.CharField(max_length=200, verbose_name='Monat'),
        ),
        migrations.AlterField(
            model_name='musiker',
            name='kuenstler_name',
            field=models.CharField(max_length=200, verbose_name='Künstlername'),
        ),
        migrations.AlterField(
            model_name='ort',
            name='stadt',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='person',
            name='nachname',
            field=models.CharField(default='unbekannt', max_length=200),
        ),
        migrations.AlterField(
            model_name='person',
            name='original_id',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='person',
            name='vorname',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='sender',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='spielort',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='sprache',
            name='sprache',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='status',
            name='status',
            field=models.CharField(max_length=200, verbose_name='Bearbeitungsstatus'),
        ),
        migrations.AlterField(
            model_name='technik',
            name='titel',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='turnus',
            name='turnus',
            field=models.CharField(max_length=200, verbose_name='Turnus'),
        ),
        migrations.AlterField(
            model_name='veranstaltung',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='verlag',
            name='verlag_name',
            field=models.CharField(max_length=200, verbose_name='verlag'),
        ),
        migrations.AlterField(
            model_name='video',
            name='festplatte',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='video',
            name='quelle',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='video',
            name='titel',
            field=models.CharField(max_length=200),
        ),
    ]
