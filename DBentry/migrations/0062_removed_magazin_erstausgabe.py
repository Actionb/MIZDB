# Generated by Django 2.2 on 2019-10-21 08:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0061_alter_ausgabe_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='magazin',
            name='erstausgabe',
        ),
    ]