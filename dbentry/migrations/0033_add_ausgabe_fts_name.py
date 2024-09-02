# Generated by Django 4.2.15 on 2024-08-19 11:12

import dbentry.fts.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dbentry", "0032_alter_ausgabe_e_datum"),
    ]

    operations = [
        migrations.AddField(
            model_name="ausgabe",
            name="_fts_name",
            field=models.CharField(default="", editable=False, max_length=200),
        ),
        migrations.AlterField(
            model_name="ausgabe",
            name="_fts",
            field=dbentry.fts.fields.SearchVectorField(
                columns=[
                    dbentry.fts.fields.WeightedColumn(
                        "_fts_name", "A", "simple_unaccent"
                    ),
                    dbentry.fts.fields.WeightedColumn(
                        "beschreibung", "C", "german_unaccent"
                    ),
                    dbentry.fts.fields.WeightedColumn(
                        "bemerkungen", "D", "simple_unaccent"
                    ),
                ]
            ),
        ),
    ]