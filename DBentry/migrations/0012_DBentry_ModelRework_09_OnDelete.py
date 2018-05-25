# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-27 08:39
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0011_DBentry_ModelRework_08_BeschreibungBemerkungFields'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='m2m_datei_musiker',
            options={'verbose_name': 'Musiker', 'verbose_name_plural': 'Musiker'},
        ),
        migrations.AlterField(
            model_name='audio',
            name='sender',
            field=models.ForeignKey(blank=True, help_text='Name des Radio-/Fernsehsenders', null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.sender'),
        ),
        migrations.AlterField(
            model_name='band',
            name='herkunft',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.ort'),
        ),
        migrations.AlterField(
            model_name='bestand',
            name='lagerort',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='DBentry.lagerort'),
        ),
        migrations.AlterField(
            model_name='bestand',
            name='provenienz',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.provenienz'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='buch_serie',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.buch_serie', verbose_name='Buchserie'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='sprache',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.sprache'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='sprache_orig',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='buch_orig_set', to='DBentry.sprache', verbose_name='Sprache (Original)'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='verlag',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.verlag'),
        ),
        migrations.AlterField(
            model_name='buch',
            name='verlag_orig',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='buch_orig_set', to='DBentry.verlag', verbose_name='Verlag (Original)'),
        ),
        migrations.AlterField(
            model_name='format',
            name='format_size',
            field=models.ForeignKey(blank=True, help_text='LP, 12", Mini-Disc, etc.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.FormatSize', verbose_name='Format Größe'),
        ),
        migrations.AlterField(
            model_name='format',
            name='format_typ',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='DBentry.FormatTyp', verbose_name='Format Typ'),
        ),
        migrations.AlterField(
            model_name='magazin',
            name='verlag',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.verlag'),
        ),
        migrations.AlterField(
            model_name='musiker',
            name='person',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.person'),
        ),
        migrations.AlterField(
            model_name='ort',
            name='bland',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.bundesland', verbose_name='Bundesland'),
        ),
        migrations.AlterField(
            model_name='person',
            name='herkunft',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.ort'),
        ),
        migrations.AlterField(
            model_name='provenienz',
            name='geber',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='DBentry.geber'),
        ),
        migrations.AlterField(
            model_name='schlagwort',
            name='ober',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='unterbegriffe', to='DBentry.schlagwort', verbose_name='Oberbegriff'),
        ),
        migrations.AlterField(
            model_name='spielort',
            name='ort',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='DBentry.ort'),
        ),
        migrations.AlterField(
            model_name='veranstaltung',
            name='spielort',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='DBentry.spielort'),
        ),
        migrations.AlterField(
            model_name='video',
            name='sender',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='DBentry.sender'),
        ),
    ]