# Generated by Django 2.2.16 on 2020-10-28 08:25

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0011_remove_video_tracks'),
    ]

    operations = [
        migrations.RenameField(
            model_name='audio',
            old_name='e_jahr',
            new_name='jahr',
        ),
        migrations.AddField(
            model_name='audio',
            name='medium_qty',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Anzahl'),
        ),
        migrations.AddField(
            model_name='audio',
            name='original',
            field=models.BooleanField(default=False, help_text='Original/Kopie', verbose_name='Original'),
        ),
        migrations.AddField(
            model_name='video',
            name='medium_qty',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Anzahl'),
        ),
        migrations.AddField(
            model_name='video',
            name='original',
            field=models.BooleanField(default=False, help_text='Original/Kopie', verbose_name='Original'),
        ),
        migrations.AlterField(
            model_name='audio',
            name='medium',
            field=models.ForeignKey(blank=True, help_text='Format des Speichermediums.', null=True, on_delete=django.db.models.deletion.PROTECT, to='dbentry.AudioMedium', verbose_name='Speichermedium'),
        ),
        migrations.AlterField(
            model_name='audio',
            name='quelle',
            field=models.CharField(blank=True, help_text='Angaben zur Herkunft/Qualität der Aufnahme: z.B. Broadcast, Live, etc.', max_length=200),
        ),
        migrations.AlterField(
            model_name='video',
            name='medium',
            field=models.ForeignKey(blank=True, help_text='Format des Speichermediums.', null=True, on_delete=django.db.models.deletion.PROTECT, to='dbentry.VideoMedium', verbose_name='Speichermedium'),
        ),
        migrations.AlterField(
            model_name='video',
            name='quelle',
            field=models.CharField(blank=True, help_text='Angaben zur Herkunft/Qualität der Aufnahme: z.B. Broadcast, Live, etc.', max_length=200),
        ),
    ]