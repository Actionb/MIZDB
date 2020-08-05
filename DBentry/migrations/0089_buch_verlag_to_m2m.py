# Generated by Django 2.2 on 2020-07-09 08:53

from django.db import migrations, models


class Migration(migrations.Migration):

    def fk_to_temp(apps, schema_editor):
        """Copy the ids of the verlag ForeignKey field to the temp field."""
        buch = apps.get_model('DBentry', 'buch')
        buch.objects.exclude(verlag__isnull=True).update(verlag_temp=models.F('verlag'))

    def temp_to_fk(apps, schema_editor):
        """Copy the ids back from the temp field to the ForeignKey field."""
        buch = apps.get_model('DBentry', 'buch')
        buch.objects.exclude(verlag_temp='').update(verlag_id=models.F('verlag_temp'))

    def temp_to_m2m(apps, schema_editor):
        """Copy the ids to the m2m relation."""
        buch = apps.get_model('DBentry', 'buch')
        values = buch.objects.exclude(verlag_temp='').values_list('pk', 'verlag_temp')
        m2m_model = buch._meta.get_field('verlag').remote_field.through
        m2m_model.objects.bulk_create([
            m2m_model(buch_id=int(pk), verlag_id=int(verlag_id))
            for pk, verlag_id in values
        ])

    def m2m_to_temp(apps, schema_editor):
        """Copy the ids back from the m2m relation to the temp field."""
        buch = apps.get_model('DBentry', 'buch')
        for obj in buch.objects.all():
            v = obj.verlag.first()
            if v:
                obj.verlag_temp = str(v.pk)
                obj.save()

    dependencies = [
        ('DBentry', '0088_artikel_meta_ordering'),
    ]

    operations = [
        migrations.AddField(
            model_name='buch',
            name='verlag_temp',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RunPython(fk_to_temp, temp_to_fk),
        migrations.RemoveField(
            model_name='buch',
            name='verlag',
        ),
        migrations.AddField(
            model_name='buch',
            name='verlag',
            field=models.ManyToManyField(to='DBentry.verlag'),
        ),
        migrations.RunPython(temp_to_m2m, m2m_to_temp),
        migrations.RemoveField(
            model_name='buch',
            name='verlag_temp',
        ),
    ]