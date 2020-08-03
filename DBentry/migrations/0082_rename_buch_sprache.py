# Generated by Django 2.2 on 2019-10-24 09:20
# Change buch.sprache from a ForeignKey to model 'sprache' to a CharField with
# the values of sprache.sprache.
# Then delete model 'sprache'.

from django.db import migrations, models

def forwards(apps, schema_editor):
    """
    Set the values of the new CharField 'sprache' to the values of the old
    ForeignKey field 'sprache_OLD'.
    """
    buch = apps.get_model('DBentry', 'buch')
    db_alias = schema_editor.connection.alias
    queryset = buch.objects.using(db_alias).exclude(sprache_OLD__isnull=True)
    for obj in queryset:
        buch.objects.filter(pk=obj.pk).update(sprache=obj.sprache_OLD.sprache)


class Migration(migrations.Migration):

    dependencies = [
        ('DBentry', '0081_delete_model_sender'),
    ]

    operations = [
        migrations.RenameField(
            model_name='buch',
            old_name='sprache',
            new_name='sprache_OLD',
        ),
        migrations.AddField(
            model_name='buch',
            name='sprache',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='buch',
            name='sprache_OLD',
        ),
        migrations.DeleteModel(
            name='sprache',
        ),
    ]
