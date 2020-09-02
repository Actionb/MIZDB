# Generated by Django 2.2.13 on 2020-09-02 09:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0003_video_model'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bandalias',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'ordering': ['alias'], 'verbose_name': 'Alias', 'verbose_name_plural': 'Aliases'},
        ),
        migrations.AlterModelOptions(
            name='genrealias',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'ordering': ['alias'], 'verbose_name': 'Alias', 'verbose_name_plural': 'Aliases'},
        ),
        migrations.AlterModelOptions(
            name='musikeralias',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'ordering': ['alias'], 'verbose_name': 'Alias', 'verbose_name_plural': 'Aliases'},
        ),
        migrations.AlterModelOptions(
            name='schlagwortalias',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'ordering': ['alias'], 'verbose_name': 'Alias', 'verbose_name_plural': 'Aliases'},
        ),
        migrations.AlterModelOptions(
            name='spielortalias',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'ordering': ['alias'], 'verbose_name': 'Alias', 'verbose_name_plural': 'Aliases'},
        ),
        migrations.AlterModelOptions(
            name='veranstaltungalias',
            options={'default_permissions': ('add', 'change', 'delete', 'merge', 'view'), 'ordering': ['alias'], 'verbose_name': 'Alias', 'verbose_name_plural': 'Aliases'},
        ),
    ]
