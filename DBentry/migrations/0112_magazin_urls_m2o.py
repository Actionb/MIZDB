# Generated by Django 2.2.13 on 2020-08-25 07:18

from django.db import migrations, models, transaction
import django.db.models.deletion


@transaction.atomic
def forwards(apps, schema_editor):
    """Move the urls from magazin.magazin_url to the new model MagazinURL."""
    magazin = apps.get_model('DBentry', 'magazin')
    MagazinURL = apps.get_model('DBentry', 'MagazinURL')
    objs = [
        MagazinURL(magazin_id=magazin_id, url=url)
        for magazin_id, url in magazin.objects.values_list('id', 'magazin_url')
        if url
    ]
    MagazinURL.objects.bulk_create(objs)


@transaction.atomic
def reverse(apps, schema_editor):
    """Move the first url from MagazinURL back to magazin.magazin_url."""
    magazin = apps.get_model('DBentry', 'magazin')
    for mag in magazin.objects.exclude(urls__isnull=True):
        url = mag.urls.first().url
        if url:
            mag.magazin_url = url
            mag.save()


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0111_brochure_meta_inheritance'),
    ]

    operations = [
        migrations.CreateModel(
            name='MagazinURL',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(blank=True, verbose_name='Webpage')),
                ('magazin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='urls', to='DBentry.magazin')),
            ],
            options={
                'default_permissions': ('add', 'change', 'delete', 'merge', 'view'),
                'verbose_name': 'Web-Adresse',
                'abstract': False,
                'verbose_name_plural': 'Web-Adressen',
            },
        ),
        migrations.RunPython(forwards, reverse, elidable=True),
        migrations.RemoveField(
            model_name='magazin',
            name='magazin_url',
        ),
    ]