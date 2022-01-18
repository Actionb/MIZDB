# Generated by Django 2.2.16 on 2021-10-06 08:41

from django.contrib.postgres.operations import CreateExtension, UnaccentExtension
from django.db import migrations

import dbentry.fts.fields

import tsvector_field


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0026_url_model_verbose_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='artikel',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('schlagzeile', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('zusammenfassung', 'B', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='audio',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='audiomedium',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('medium', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='ausgabe',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('_name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='autor',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('_name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='band',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('band_name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='bandalias',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('alias', 'B', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='bildreihe',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('name', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='buch',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='bundesland',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('bland_name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('code', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='datei',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='dokument',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='foto',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='geber',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('name', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='genre',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('genre', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='genrealias',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('alias', 'B', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='herausgeber',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('herausgeber', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='instrument',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('instrument', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('kuerzel', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='lagerort',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('_name', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='land',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('land_name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('code', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='magazin',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('magazin_name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('issn', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='memorabilien',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='monat',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('monat', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('abk', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='musiker',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('kuenstler_name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='musikeralias',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('alias', 'B', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='ort',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('_name', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='person',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('_name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='plakat',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('signatur', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='plattenfirma',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('name', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='schlagwort',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('schlagwort', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='schlagwortalias',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('alias', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='schriftenreihe',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('name', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='spielort',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='spielortalias',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('alias', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='technik',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='veranstaltung',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('name', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('datum', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='veranstaltungalias',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('alias', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='veranstaltungsreihe',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('name', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='verlag',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('verlag_name', 'A', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='video',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='videomedium',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('medium', 'A', 'simple_unaccent')]),
        ),
        # Add the text search dictionary that removes a prefixed hyphen/dash
        # from a numerical string.
        # This is required to make strings such as '2018-01' intuitive to
        # search for:
        # to_tsvector('simple', '2018-01')          => '-01':2 '2018':1
        # to_tsquery('simple', '2018-01')           => '2018' & '-01'
        # to_tsvector('simple_numeric', '2018-01')  => '01':2 '2018':1
        # to_tsquery('simple_numeric', '2018-01')   => '2018' & '01'
        CreateExtension('dict_int'),
        migrations.RunSQL(
            sql=(
                "CREATE TEXT SEARCH DICTIONARY signed_numeric (TEMPLATE = intdict_template);"
                "ALTER TEXT SEARCH DICTIONARY signed_numeric (absval = true);"
            ),
            reverse_sql=(
                "DROP TEXT SEARCH DICTIONARY IF EXISTS signed_numeric CASCADE;"
            )
        ),
        # Use postgres unaccent:
        UnaccentExtension(),
        migrations.RunSQL(
            sql=(
                "CREATE TEXT SEARCH CONFIGURATION simple_unaccent (COPY = simple);"
                "ALTER TEXT SEARCH CONFIGURATION simple_unaccent ALTER MAPPING FOR hword, hword_part, word WITH unaccent, simple;"
                "ALTER TEXT SEARCH CONFIGURATION simple_unaccent ALTER MAPPING FOR int, uint WITH signed_numeric;"
                "CREATE TEXT SEARCH CONFIGURATION german_unaccent (COPY = german);"
                "ALTER TEXT SEARCH CONFIGURATION german_unaccent ALTER MAPPING FOR hword, hword_part, word WITH unaccent, german_stem;"
                "CREATE TEXT SEARCH CONFIGURATION english_unaccent (COPY = english);"
                "ALTER TEXT SEARCH CONFIGURATION english_unaccent ALTER MAPPING FOR hword, hword_part, word WITH unaccent, english_stem;"
            ),
            reverse_sql=(
                "DROP TEXT SEARCH CONFIGURATION IF EXISTS simple_unaccent CASCADE;"
                "DROP TEXT SEARCH CONFIGURATION IF EXISTS german_unaccent CASCADE;"
                "DROP TEXT SEARCH CONFIGURATION IF EXISTS english_unaccent CASCADE;"
            )
        ),
        tsvector_field.IndexSearchVector('artikel', '_fts'),
        tsvector_field.IndexSearchVector('audio', '_fts'),
        tsvector_field.IndexSearchVector('audiomedium', '_fts'),
        tsvector_field.IndexSearchVector('ausgabe', '_fts'),
        tsvector_field.IndexSearchVector('autor', '_fts'),
        tsvector_field.IndexSearchVector('band', '_fts'),
        tsvector_field.IndexSearchVector('bandalias', '_fts'),
        tsvector_field.IndexSearchVector('bildreihe', '_fts'),
        tsvector_field.IndexSearchVector('buch', '_fts'),
        tsvector_field.IndexSearchVector('bundesland', '_fts'),
        tsvector_field.IndexSearchVector('datei', '_fts'),
        tsvector_field.IndexSearchVector('dokument', '_fts'),
        tsvector_field.IndexSearchVector('foto', '_fts'),
        tsvector_field.IndexSearchVector('geber', '_fts'),
        tsvector_field.IndexSearchVector('genre', '_fts'),
        tsvector_field.IndexSearchVector('genrealias', '_fts'),
        tsvector_field.IndexSearchVector('herausgeber', '_fts'),
        tsvector_field.IndexSearchVector('instrument', '_fts'),
        tsvector_field.IndexSearchVector('lagerort', '_fts'),
        tsvector_field.IndexSearchVector('land', '_fts'),
        tsvector_field.IndexSearchVector('magazin', '_fts'),
        tsvector_field.IndexSearchVector('memorabilien', '_fts'),
        tsvector_field.IndexSearchVector('monat', '_fts'),
        tsvector_field.IndexSearchVector('musiker', '_fts'),
        tsvector_field.IndexSearchVector('musikeralias', '_fts'),
        tsvector_field.IndexSearchVector('ort', '_fts'),
        tsvector_field.IndexSearchVector('person', '_fts'),
        tsvector_field.IndexSearchVector('plakat', '_fts'),
        tsvector_field.IndexSearchVector('plattenfirma', '_fts'),
        tsvector_field.IndexSearchVector('schlagwort', '_fts'),
        tsvector_field.IndexSearchVector('schlagwortalias', '_fts'),
        tsvector_field.IndexSearchVector('schriftenreihe', '_fts'),
        tsvector_field.IndexSearchVector('spielort', '_fts'),
        tsvector_field.IndexSearchVector('spielortalias', '_fts'),
        tsvector_field.IndexSearchVector('technik', '_fts'),
        tsvector_field.IndexSearchVector('veranstaltung', '_fts'),
        tsvector_field.IndexSearchVector('veranstaltungalias', '_fts'),
        tsvector_field.IndexSearchVector('veranstaltungsreihe', '_fts'),
        tsvector_field.IndexSearchVector('verlag', '_fts'),
        tsvector_field.IndexSearchVector('video', '_fts'),
        tsvector_field.IndexSearchVector('videomedium', '_fts'),
        migrations.AddField(
            model_name='basebrochure',
            name='_base_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('titel', 'A', 'simple_unaccent'), dbentry.fts.fields.WeightedColumn('zusammenfassung', 'B', 'german_unaccent'), dbentry.fts.fields.WeightedColumn('bemerkungen', 'D', 'simple_unaccent')]),
        ),
        migrations.AddField(
            model_name='brochure',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent')]),
        ),
        migrations.AddField(
            model_name='kalender',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent')]),
        ),
        migrations.AddField(
            model_name='katalog',
            name='_fts',
            field=dbentry.fts.fields.SearchVectorField(columns=[dbentry.fts.fields.WeightedColumn('beschreibung', 'C', 'german_unaccent')]),
        ),
        tsvector_field.IndexSearchVector('basebrochure', '_base_fts'),
        tsvector_field.IndexSearchVector('brochure', '_fts'),
        tsvector_field.IndexSearchVector('kalender', '_fts'),
        tsvector_field.IndexSearchVector('katalog', '_fts'),
    ]
