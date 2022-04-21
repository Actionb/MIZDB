from functools import partial
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib import auth
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import exceptions
from django.db import models

from dbentry import utils
from tests.case import MIZTestCase


class M2MTarget(models.Model):
    pass


class M2MSource(models.Model):
    targets = models.ManyToManyField('test_utils.M2MTarget', related_name='sources')


class Protector(models.Model):
    date = models.DateField(blank=True, null=True)


class Protected(models.Model):
    protector = models.ForeignKey('test_utils.Protector', on_delete=models.PROTECT)


class TestModelUtils(MIZTestCase):

    def test_is_protected(self):
        protector = Protector()
        protector.save()
        protected = Protected(protector=protector)
        protected.save()
        # is_protected will just return None if the object isn't protected
        self.assertIsNotNone(utils.is_protected([protector]))
        self.assertIsNone(utils.is_protected([protected]))

    def test_get_model_from_string(self):
        self.assertEqual(
            Protected,
            utils.get_model_from_string('Protected', app_label='test_utils')
        )
        self.assertEqual(Protected, utils.get_model_from_string('test_utils.protected'))
        with self.assertRaises(LookupError):
            utils.get_model_from_string('beep boop')
        with self.assertRaises(LookupError):
            utils.get_model_from_string('Protected', app_label='beep boop')

    def test_get_reverse_field_path(self):
        # The relation has no 'related_query_name' or 'related_name';
        # get_reverse_field_path should use the model_name of the related model
        # noinspection PyUnresolvedReferences
        rel = Protector._meta.get_field('protected')
        self.assertEqual(utils.get_reverse_field_path(rel, 'name'), 'protected__name')
        # noinspection PyUnresolvedReferences
        rel = M2MTarget._meta.get_field('sources')
        self.assertEqual(utils.get_reverse_field_path(rel, 'name'), 'sources__name')
        rel.related_query_name = 'foobar'
        self.assertEqual(utils.get_reverse_field_path(rel, 'name'), 'foobar__name')

    def test_get_fields_and_lookups(self):
        fields, lookups = utils.get_fields_and_lookups(Protected, 'protector__date__year__gte')
        # noinspection PyUnresolvedReferences
        self.assertEqual(
            fields,
            [Protected._meta.get_field('protector'), Protector._meta.get_field('date')]
        )
        self.assertEqual(lookups, ['year', 'gte'])

    def test_get_fields_and_lookups_invalid_lookup(self):
        """
        Assert that get_fields_and_lookups raises FieldError on encountering an
        invalid lookup.
        """
        with self.assertRaises(exceptions.FieldError):
            utils.get_fields_and_lookups(Protected, 'protector__date__hour')

    def test_get_fields_and_lookups_field_does_not_exist(self):
        """
        Assert that get_fields_and_lookups raises FieldDoesNotExist if the first
        field is not a model field of the given model.
        """
        with self.assertRaises(exceptions.FieldDoesNotExist):
            utils.get_fields_and_lookups(Protected, 'nofield__icontains')

    def test_clean_contenttypes(self):
        """
        clean_contenttypes should delete CT objects with invalid models.
        """
        exists = ContentType.objects.get_for_model(Protected)
        not_exists = ContentType.objects.create(app_label='utils', model='NotExists')
        content_types = Mock(return_value=[exists, not_exists])
        stream = StringIO()
        with patch.object(ContentType.objects, 'all', new=content_types):
            utils.clean_contenttypes(stream)
        self.assertIn('Deleting NotExists', stream.getvalue())
        self.assertFalse(ContentType.objects.filter(model='NotExists').exists())
        self.assertTrue(ContentType.objects.filter(pk=exists.pk).exists())


####################################################################################################
# get_model_relations tests
####################################################################################################

class OneToOneModel(models.Model):
    pass


class ForwardRelatedModel(models.Model):
    pass


class ReverseRelatedModel(models.Model):
    reverse = models.ForeignKey('test_utils.AllRelations', on_delete=models.CASCADE)


class M2MTargetOne(models.Model):
    pass


class M2MTargetTwo(models.Model):
    pass


class M2MTable(models.Model):
    source = models.ForeignKey('test_utils.AllRelations', on_delete=models.CASCADE)
    target = models.ForeignKey('test_utils.M2MTargetTwo', on_delete=models.CASCADE)


class AllRelations(models.Model):
    one_to_one = models.OneToOneField('test_utils.OneToOneModel', on_delete=models.CASCADE)
    forward_related = models.ForeignKey('test_utils.ForwardRelatedModel', on_delete=models.CASCADE)
    many_auto = models.ManyToManyField('test_utils.M2MTargetOne')
    many_intermediary = models.ManyToManyField('test_utils.M2MTargetTwo', through='test_utils.M2MTable')  # noqa


class TestGetModelRelations(MIZTestCase):

    def test_get_model_relations(self):
        # noinspection PyUnresolvedReferences
        o2o = AllRelations._meta.get_field('one_to_one').remote_field
        # noinspection PyUnresolvedReferences
        fk = AllRelations._meta.get_field('forward_related').remote_field
        # noinspection PyUnresolvedReferences
        rev_fk = ReverseRelatedModel._meta.get_field('reverse').remote_field
        # noinspection PyUnresolvedReferences
        m2m_inter = AllRelations._meta.get_field('many_intermediary').remote_field
        # noinspection PyUnresolvedReferences
        m2m_auto = AllRelations._meta.get_field('many_auto').remote_field

        rels = utils.get_model_relations(AllRelations)
        self.assertIn(o2o, rels)
        self.assertIn(fk, rels)
        self.assertIn(rev_fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)

        rels = utils.get_model_relations(AllRelations, reverse=False)
        self.assertIn(o2o, rels)
        self.assertIn(fk, rels)
        self.assertNotIn(rev_fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)

        rels = utils.get_model_relations(AllRelations, forward=False)
        self.assertNotIn(o2o, rels)
        self.assertNotIn(fk, rels)
        self.assertIn(rev_fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)

        rels = utils.get_model_relations(AllRelations, forward=False, reverse=False)
        self.assertNotIn(o2o, rels)
        self.assertNotIn(fk, rels)
        self.assertNotIn(rev_fk, rels)
        self.assertIn(m2m_inter, rels)
        self.assertIn(m2m_auto, rels)


####################################################################################################
# get_updatable_fields test
####################################################################################################

class UpdatableFieldsModel(models.Model):
    empty_one = models.IntegerField(null=True)
    empty_two = models.CharField(max_length=100, blank=True)
    not_empty = models.CharField(max_length=100)
    has_default = models.CharField(max_length=100, default='Sausages')
    _private_field = models.CharField(max_length=100, blank=True)
    nullable_boolean_field = models.BooleanField(null=True)
    boolean_field_default = models.BooleanField(default=False)


class TestGetUpdatableFields(MIZTestCase):

    def test_get_updatable_fields(self):
        obj = UpdatableFieldsModel(not_empty='Eggs & Spam', has_default='Sausages')
        self.assertEqual(
            utils.get_updatable_fields(obj),
            ['empty_one', 'empty_two', 'has_default', 'nullable_boolean_field']
        )
        obj.empty_one = 1
        self.assertNotIn('empty_one', utils.get_updatable_fields(obj))
        obj.has_default = 'Bacon'
        self.assertNotIn('has_default', utils.get_updatable_fields(obj))


####################################################################################################
# clean_permissions tests
####################################################################################################


class Spam(models.Model):
    class Meta:
        default_permissions = ('add', 'change', 'delete', 'view', 'eat')


class TestCleanPerms(MIZTestCase):

    def setUp(self):
        super().setUp()
        self.patcher = partial(patch.object, Permission.objects, 'all')

    def test_unknown_model(self):
        """
        Assert that a message is written to the stream if clean_permissions
        encounters a content type with an unknown model.
        """
        ct = ContentType.objects.create(model='Viking', app_label='utils')
        p = Permission.objects.create(name='Can add spam', content_type=ct, codename='add_spam')
        expected_message = (
            f"ContentType of {p.name} references unknown model: "
            f"{p.content_type.app_label}.{p.content_type.model}\n"
            "Try running clean_contenttypes.\n"
        )
        stream = StringIO()
        with self.patcher(new=Mock(return_value=[p])):
            utils.clean_permissions(stream)
        self.assertEqual(stream.getvalue(), expected_message)

    def test_only_default_perms(self):
        """
        Assert that clean_permissions only works on model default permissions.
        """
        p1 = Permission.objects.get(codename='eat_spam')
        # Change the codename so that clean_permissions has something to clean:
        p1.codename = 'eat_lovelyspam'
        p1.save()
        # Add a permission that isn't a default permission of 'Spam':
        ct = ContentType.objects.get_for_model(Spam)
        p2 = Permission.objects.create(
            name='Can reject spam', codename='reject_spam', content_type=ct
        )
        stream = StringIO()
        with self.patcher(new=Mock(return_value=[p1, p2])):
            utils.clean_permissions(stream)
        self.assertTrue(stream.getvalue())
        p1.refresh_from_db()
        self.assertEqual(p1.codename, 'eat_spam', msg="p1.codename should have been reset")
        p2.refresh_from_db()
        self.assertEqual(p2.codename, 'reject_spam', msg="p2.codename should have not been altered")

    def test_no_update_needed(self):
        """
        Assert that clean_permissions only updates a permission's codename if
        that codename differs from the one returned by get_permission_codename.
        """
        p = Permission.objects.get(codename='eat_spam')
        p.codename = 'eat_lovelyspam'
        p.save()
        stream = StringIO()
        mocked_get_codename = Mock(return_value='eat_lovelyspam')
        with patch.object(auth, 'get_permission_codename', new=mocked_get_codename):
            with self.patcher(new=Mock(return_value=[p])):
                utils.clean_permissions(stream)
        self.assertFalse(stream.getvalue())
        p.refresh_from_db()
        self.assertEqual(p.codename, 'eat_lovelyspam')

    def test_duplicate_permissions(self):
        """Assert that clean_permissions deletes redundant permissions."""
        p = Permission.objects.get(codename='eat_spam')
        # Create a copy of the perm with a different codename.
        # clean_permissions will correct the codename, thus making the new perm
        # an exact duplicate of 'p'.
        new = Permission.objects.create(
            name=p.name, codename='eat_lovelyspam', content_type=p.content_type
        )
        expected_message = (
            "Permission with codename 'eat_spam' already exists. "
            "Deleting permission with outdated codename: 'eat_lovelyspam'\n"
        )
        stream = StringIO()
        with self.patcher(new=Mock(return_value=[new])):
            utils.clean_permissions(stream)
        self.assertEqual(stream.getvalue(), expected_message)
        self.assertFalse(new.pk)
