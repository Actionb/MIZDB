# Generated by Django 2.2 on 2019-10-23 12:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0072_removed_Format_channel'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='format',
            name='noise_red',
        ),
    ]
