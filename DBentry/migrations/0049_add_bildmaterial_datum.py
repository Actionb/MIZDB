# Generated by Django 2.2 on 2019-06-03 10:20

import DBentry.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0048_bildmaterial_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='bildmaterial',
            name='datum',
            field=DBentry.fields.PartialDateField(blank=True, max_length=10),
        ),
    ]
