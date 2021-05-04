# Generated by Django 2.2.16 on 2021-01-26 12:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0018_Brochure_model_meta_inheritance'),
    ]

    operations = [
        migrations.AddField(
            model_name='audio',
            name='land_pressung',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='dbentry.Land', verbose_name='Land der Pressung'),
        ),
    ]