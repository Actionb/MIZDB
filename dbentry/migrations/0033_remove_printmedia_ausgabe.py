# Generated by Django 4.1.9 on 2023-06-13 07:10

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dbentry", "0032_alter_printmedia__brochure_ptr"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="printmedia",
            name="ausgabe",
        ),
    ]
