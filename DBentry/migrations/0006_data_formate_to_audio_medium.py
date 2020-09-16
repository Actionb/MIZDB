# Generated by Django 2.2.13 on 2020-09-03 09:27
import os

from django.core import serializers
from django.db import migrations, transaction


dump_file = 'format_models.json'


@transaction.atomic
def to_audio_medium(apps, schema_editor):
    Audio = apps.get_model('DBentry', 'Audio')
    AudioMedium = apps.get_model('DBentry', 'AudioMedium')
    Format = apps.get_model('DBentry', 'Format')
    FormatTyp = apps.get_model('DBentry', 'FormatTyp')
    for format_typ in FormatTyp.objects.all():
        medium = AudioMedium.objects.create(medium=format_typ.typ)
        formate = Format.objects.filter(format_typ=format_typ)
        Audio.objects.filter(format__in=formate).update(medium=medium)
    # Dump the data of the models to be deleted:
    for model_name in ('FormatTyp', 'FormatSize', 'FormatTag', 'Format', 'Format_tag'):
        model = apps.get_model('DBentry', model_name)
        with open('%s.json' % model_name, 'w') as stream:
            serializers.serialize('json', model.objects.iterator(), stream=stream)


def to_formate(apps, schema_editor):
    with transaction.atomic():
        for model_name in (
                'FormatTyp', 'FormatSize', 'FormatTag', 'Format', 'Format_tag'):
            model = apps.get_model('DBentry', model_name)
            try:
                data = open('%s.json' % model_name, 'r').read()
            except FileNotFoundError:
                continue
            if data:
                objects = [d.object for d in serializers.deserialize('json', data)]
                model.objects.bulk_create(objects)
    for model_name in ('FormatTyp', 'FormatSize', 'FormatTag', 'Format', 'Format_tag'):
        try:
            os.remove('%s.json' % model_name)
        except FileNotFoundError:
            continue


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0005_add_model_audio_medium'),
    ]

    operations = [
        migrations.RunPython(to_audio_medium, to_formate, elidable=True),
    ]
