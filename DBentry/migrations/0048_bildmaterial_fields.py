# Generated by Django 2.2 on 2019-05-17 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0047_removed_alter_data_ausgabe_perm'),
    ]

    operations = [
        migrations.AddField(
            model_name='bildmaterial',
            name='signatur',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='bildmaterial',
            name='size',
            field=models.CharField(blank=True, max_length=200, verbose_name='Größe'),
        ),
    ]
