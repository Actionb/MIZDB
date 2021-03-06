# Generated by Django 2.2.13 on 2020-09-02 09:34

import dbentry.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dbentry', '0002_rename_kalendar_to_kalender'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoMedium',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('medium', models.CharField(max_length=200)),
            ],
            options={
                'verbose_name': 'Video-Medium',
                'abstract': False,
                'ordering': ['medium'],
                'verbose_name_plural': 'Video-Medium',
                'default_permissions': ('add', 'change', 'delete', 'merge', 'view'),
            },
        ),
        migrations.RemoveField(
            model_name='video',
            name='festplatte',
        ),
        migrations.AddField(
            model_name='video',
            name='jahr',
            field=dbentry.fields.YearField(blank=True, null=True, verbose_name='Jahr'),
        ),
        migrations.AddField(
            model_name='video',
            name='ort',
            field=models.ManyToManyField(to='dbentry.Ort'),
        ),
        migrations.AlterField(
            model_name='audio',
            name='beschreibung',
            field=models.TextField(blank=True, help_text='Beschreibung bzgl. des Audio Materials'),
        ),
        migrations.AlterField(
            model_name='audio',
            name='laufzeit',
            field=models.DurationField(blank=True, help_text='Format: hh:mm:ss. Beispiel Laufzeit von 144 Minuten: 0:144:0.', null=True),
        ),
        migrations.AlterField(
            model_name='video',
            name='beschreibung',
            field=models.TextField(blank=True, help_text='Beschreibung bzgl. des Video Materials'),
        ),
        migrations.AlterField(
            model_name='video',
            name='laufzeit',
            field=models.DurationField(blank=True, help_text='Format: hh:mm:ss. Beispiel Laufzeit von 144 Minuten: 0:144:0.', null=True),
        ),
        migrations.AlterField(
            model_name='video',
            name='quelle',
            field=models.CharField(blank=True, help_text='Broadcast, Live, etc.', max_length=200),
        ),
        migrations.AddField(
            model_name='video',
            name='medium',
            field=models.ForeignKey(blank=True, help_text='Format des Speichermediums.', null=True, on_delete=django.db.models.deletion.PROTECT, to='dbentry.VideoMedium', verbose_name='Medium'),
        ),
    ]
