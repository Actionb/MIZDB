# Generated by Django 2.2.16 on 2020-10-29 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0015_add_default_to_medium_qty'),
    ]

    operations = [
        migrations.AlterField(
            model_name='videomedium',
            name='medium',
            field=models.CharField(max_length=200, unique=True),
        ),
    ]
