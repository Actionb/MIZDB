from unittest import mock
from unittest.mock import Mock, patch

from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db import models as django_models

from dbentry.base.models import BaseModel
from tests.case import MIZTestCase
from tests.factory import make
from tests.test_base.models import Audio, MusikerAudioM2M, Person


class TestBaseModel(MIZTestCase):
    model = Audio

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(
            cls.model, titel='Alice Tester', other_title='Beats To Write Tests To',
            beschreibung='They test things.'
        )
        super().setUpTestData()

    def test_qs(self):
        # noinspection PyUnresolvedReferences
        queryset = self.obj.qs()
        self.assertIsInstance(queryset, django_models.QuerySet)
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.obj, queryset)

    def test_qs_exception(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            self.model.qs(self.model)

    def test_str_name_field_set(self):
        """With a name_field set, str() should use that field's value."""
        self.obj.name_field = 'titel'
        self.assertEqual(self.obj.__str__(), 'Alice Tester')

    def test_str_no_name_field_set(self):
        """
        When no name_field is set, str() should concatenate the values of all
        fields that aren't empty, relations or explicitly excluded.
        """
        self.obj.name_field = ''
        self.obj.exclude_from_str = ['beschreibung']
        self.assertEqual(self.obj.__str__(), 'Alice Tester Beats To Write Tests To')
        # Empty values should be ignored:
        self.obj.titel = ''
        self.assertEqual(self.obj.__str__(), 'Beats To Write Tests To')

    def test_merge_permission(self):
        """Assert that the model has the new 'merge' permission."""
        ct = ContentType.objects.get_for_model(self.model)
        # noinspection PyUnresolvedReferences
        self.assertIn(
            get_permission_codename('merge', self.model._meta),
            Permission.objects.filter(content_type=ct).values_list('codename', flat=True)
        )


class TestBaseM2MModel(MIZTestCase):
    model = MusikerAudioM2M

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(
            cls.model, audio__titel='Testaudio', musiker__kuenstler_name='Alice Tester'
        )
        super().setUpTestData()

    def test_str_name_field_set(self):
        """With a name_field set, str() should use that field's related value."""
        self.obj.name_field = 'musiker'
        self.assertEqual(self.obj.__str__(), "Alice Tester")

    def test_str_no_name_field_set(self):
        # Without name_field.
        self.obj.name_field = ''
        self.assertEqual(self.obj.__str__(), "Testaudio (Alice Tester)")

        # When there is only one field (or less) with values, str should call
        # the super method.
        with patch('dbentry.base.models.get_model_fields') as mocked_get_fields:
            with patch.object(BaseModel, '__str__') as mocked_super:
                mocked_get_fields.return_value = [Mock(null=True)]
                self.obj.__str__()
                self.assertTrue(mocked_super.called)


class TestComputedNameModel(MIZTestCase):
    model = Person

    @classmethod
    def setUpTestData(cls):
        # noinspection PyTypeChecker
        cls.obj: Person = make(cls.model, vorname='Alice', nachname='Tester')
        # noinspection PyUnresolvedReferences
        cls.qs = cls.model.objects.filter(pk=cls.obj.pk)

        super().setUpTestData()

    def setUp(self):
        self.obj.refresh_from_db()  # TODO: might not be necessary?
        super().setUp()

    def test_init(self):
        """The name should be updated with new data upon initialization."""
        qs = self.model.objects.filter(pk=self.obj.pk)
        qs.update(vorname='Bob', _changed_flag=True)
        obj = qs.get()
        self.assertFalse(obj._changed_flag)
        self.assertEqual(obj._name, "Bob Tester")

    def test_save_no_update(self):
        """save() should not update the name, if called with update=False."""
        self.obj.vorname = 'Bob'
        self.obj._changed_flag = True
        with mock.patch.object(self.obj, 'update_name') as update_mock:
            self.obj.save(update=False)
            update_mock.assert_not_called()
        # TODO: @work: this fails; _name is changed to Bob Tester without using update_name
        self.obj.refresh_from_db()
        self.assertEqual(self.obj._name, 'Alice Tester')
        self.assertIn("Alice Tester", self.qs.values_list('_name', flat=True))

    def test_save_forces_update(self):
        """save() should update the name even if _changed_flag is False."""
        self.obj.vorname = 'Bob'
        self.obj._changed_flag = False
        self.obj.save()
        self.assertIn("Bob Tester", self.qs.values_list('_name', flat=True))

    def test_update_name(self):
        self.qs.update(vorname='Bob', _changed_flag=True)
        self.assertTrue(self.obj.update_name())
        self.assertEqual(self.obj._name, "Bob Tester")

    def test_name_default(self):
        obj = make(self.model, nachname='')
        self.assertEqual(str(obj), "No data for Person.")

    def test_update_name_no_pk(self):
        """
        Unsaved instances should always be ignored, as update_name relies on 
        filtering queries with the instance's pk.
        """
        obj = self.model()
        for forced in (True, False):
            with self.subTest(force_update=forced):
                self.assertFalse(obj.update_name(force_update=forced))

    def test_update_name_aborts_on_name_deferred(self):
        """Do not allow updating the name if field '_name' is deferred."""
        with mock.patch.object(self.obj, 'get_deferred_fields', Mock(return_value=['_name'])):
            self.assertFalse(self.obj.update_name())

    def test_update_name_resets_change_flag_after_update(self):
        """The _changed_flag should be set to False after an update."""
        self.obj._name = 'Beep'
        self.obj._changed_flag = True
        self.assertTrue(self.obj.update_name())
        self.assertFalse(self.obj._changed_flag)

    def test_update_name_resets_change_flag_after_no_update(self):
        """
        Even if the _name does not need changing, the _changed_flag should
        still be set to False.
        """
        self.qs.update(_changed_flag=True)
        self.assertFalse(self.obj.update_name())
        self.assertFalse(self.obj._changed_flag)

    def test_update_name_does_not_update_with_no_change_flag(self):
        """An update should be skipped, if the _changed_flag is False."""
        self.qs.update(_name='Beep', _changed_flag=False)
        self.assertFalse(self.obj.update_name())

    def test_update_name_changed_flag_deferred(self):
        """
        If _changed_flag is deferred, the value for it should be retrieved from
        the database directly. refresh_from_db should not be called.
        """
        obj = self.qs.defer('_changed_flag').first()
        with mock.patch.object(obj, 'refresh_from_db') as refresh_mock:
            with self.assertNumQueries(1):
                obj.update_name()
            refresh_mock.assert_not_called()

    def test_check_name_composing_fields(self):
        """
        Assert that _check_name_composing_fields identifies invalid fields in
        'name_composing_fields'.
        """
        msg_template = "Attribute 'name_composing_fields' contains invalid item: '%s'. %s"
        with patch.object(self.model, 'name_composing_fields'):
            # Invalid field:
            self.model.name_composing_fields = ['beep']
            errors = self.model._check_name_composing_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                msg_template % ('beep', "Person has no field named 'beep'")
            )
            # Invalid lookup:
            self.model.name_composing_fields = ['nachname__year']
            errors = self.model._check_name_composing_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                msg_template % ('nachname__year', "Invalid lookup: year for CharField.")
            )

    def test_check_name_composing_fields_no_attribute(self):
        """
        Assert that _check_name_composing_fields issues a warning if the
        attribute 'name_composing_fields' is not set.
        """
        with patch.object(self.model, 'name_composing_fields', new=None):
            errors = self.model._check_name_composing_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Warning)
            self.assertEqual(
                errors[0].msg,
                "You must specify the fields that make up the name by "
                "listing them in name_composing_fields."
            )
