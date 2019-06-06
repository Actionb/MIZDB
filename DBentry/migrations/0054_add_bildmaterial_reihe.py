# Generated by Django 2.2 on 2019-06-04 08:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0053_add_model_veranstaltungsreihe'),
    ]

    operations = [
        migrations.AddField(
            model_name='bildmaterial',
            name='reihe',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='DBentry.Bildreihe'),
        ),
    ]