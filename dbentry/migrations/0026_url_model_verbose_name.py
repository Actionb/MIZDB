# Generated by Django 2.2.16 on 2021-08-23 10:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0025_url_models'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='autorurl',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'verbose_name': 'Webseite', 'verbose_name_plural': 'Webseiten'},
        ),
        migrations.AlterModelOptions(
            name='bandurl',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'verbose_name': 'Webseite', 'verbose_name_plural': 'Webseiten'},
        ),
        migrations.AlterModelOptions(
            name='brochureurl',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'verbose_name': 'Webseite', 'verbose_name_plural': 'Webseiten'},
        ),
        migrations.AlterModelOptions(
            name='magazinurl',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'verbose_name': 'Webseite', 'verbose_name_plural': 'Webseiten'},
        ),
        migrations.AlterModelOptions(
            name='musikerurl',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'verbose_name': 'Webseite', 'verbose_name_plural': 'Webseiten'},
        ),
        migrations.AlterModelOptions(
            name='personurl',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'verbose_name': 'Webseite', 'verbose_name_plural': 'Webseiten'},
        ),
        migrations.AlterModelOptions(
            name='spielorturl',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'verbose_name': 'Webseite', 'verbose_name_plural': 'Webseiten'},
        ),
        migrations.AlterModelOptions(
            name='veranstaltungurl',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'verbose_name': 'Webseite', 'verbose_name_plural': 'Webseiten'},
        ),
    ]
