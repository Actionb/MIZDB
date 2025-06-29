# Generated by Django 4.2.21 on 2025-06-11 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dbentry", "0033_add_ausgabe_fts_name"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="autorurl",
            options={
                "default_permissions": ("add", "change", "delete", "merge", "view"),
                "verbose_name": "Weblink",
                "verbose_name_plural": "Weblinks",
            },
        ),
        migrations.AlterModelOptions(
            name="bandurl",
            options={
                "default_permissions": ("add", "change", "delete", "merge", "view"),
                "verbose_name": "Weblink",
                "verbose_name_plural": "Weblinks",
            },
        ),
        migrations.AlterModelOptions(
            name="brochureurl",
            options={
                "default_permissions": ("add", "change", "delete", "merge", "view"),
                "verbose_name": "Weblink",
                "verbose_name_plural": "Weblinks",
            },
        ),
        migrations.AlterModelOptions(
            name="magazinurl",
            options={
                "default_permissions": ("add", "change", "delete", "merge", "view"),
                "verbose_name": "Weblink",
                "verbose_name_plural": "Weblinks",
            },
        ),
        migrations.AlterModelOptions(
            name="musikerurl",
            options={
                "default_permissions": ("add", "change", "delete", "merge", "view"),
                "verbose_name": "Weblink",
                "verbose_name_plural": "Weblinks",
            },
        ),
        migrations.AlterModelOptions(
            name="personurl",
            options={
                "default_permissions": ("add", "change", "delete", "merge", "view"),
                "verbose_name": "Weblink",
                "verbose_name_plural": "Weblinks",
            },
        ),
        migrations.AlterModelOptions(
            name="spielorturl",
            options={
                "default_permissions": ("add", "change", "delete", "merge", "view"),
                "verbose_name": "Weblink",
                "verbose_name_plural": "Weblinks",
            },
        ),
        migrations.AlterModelOptions(
            name="veranstaltungurl",
            options={
                "default_permissions": ("add", "change", "delete", "merge", "view"),
                "verbose_name": "Weblink",
                "verbose_name_plural": "Weblinks",
            },
        ),
        migrations.AlterField(
            model_name="autorurl",
            name="url",
            field=models.URLField(verbose_name="Weblink"),
        ),
        migrations.AlterField(
            model_name="bandurl",
            name="url",
            field=models.URLField(verbose_name="Weblink"),
        ),
        migrations.AlterField(
            model_name="brochureurl",
            name="url",
            field=models.URLField(verbose_name="Weblink"),
        ),
        migrations.AlterField(
            model_name="magazinurl",
            name="url",
            field=models.URLField(verbose_name="Weblink"),
        ),
        migrations.AlterField(
            model_name="musikerurl",
            name="url",
            field=models.URLField(verbose_name="Weblink"),
        ),
        migrations.AlterField(
            model_name="personurl",
            name="url",
            field=models.URLField(verbose_name="Weblink"),
        ),
        migrations.AlterField(
            model_name="spielorturl",
            name="url",
            field=models.URLField(verbose_name="Weblink"),
        ),
        migrations.AlterField(
            model_name="veranstaltungurl",
            name="url",
            field=models.URLField(verbose_name="Weblink"),
        ),
    ]
