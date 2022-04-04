from unittest import mock
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db.models import Count
from django.test import RequestFactory, TestCase

from dbentry.base.admin import AutocompleteMixin, MIZModelAdmin
# TODO: don't forget to re-check this test module!!
from tests.case import AdminTestCase, test_site
from tests.factory import make
from tests.models import Audio, Bestand, Person, Veranstaltung


@admin.register(Audio, site=test_site)
class TestAdmin(MIZModelAdmin):
    pass


class TestAutocompleteMixin(TestCase):
    class DummyModelField:
        name = 'dummy'
        related_model = 'anything'

    def test_formfield_for_foreignkey(self):
        """
        formfield_for_foreignkey should call make_widget with tabular=True, if
        the field's name is in the inline's 'tabular_autocomplete' list.
        """
        with patch('dbentry.base.admin.super'):
            with patch('dbentry.base.admin.make_widget') as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = ['dummy']
                # noinspection PyTypeChecker
                inline.formfield_for_foreignkey(db_field=self.DummyModelField(), request=None)

                make_mock.assert_called()
                args, kwargs = make_mock.call_args
                self.assertIn('tabular', kwargs)
                self.assertTrue(kwargs['tabular'])

    def test_formfield_for_foreignkey_no_tabular(self):
        """
        formfield_for_foreignkey should call make_widget with tabular=False, if
        the field's name isn't present in the 'tabular_autocomplete' list.
        """
        with patch('dbentry.base.admin.super'):
            with patch('dbentry.base.admin.make_widget') as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = []
                # noinspection PyTypeChecker
                inline.formfield_for_foreignkey(db_field=self.DummyModelField(), request=None)

                make_mock.assert_called()
                _args, kwargs = make_mock.call_args
                self.assertIn('tabular', kwargs)
                self.assertFalse(kwargs['tabular'])

    def test_formfield_for_foreignkey_no_override(self):
        """
        formfield_for_foreignkey should not call make_widget, if a widget was
        passed in.
        """
        with patch('dbentry.base.admin.super'):
            with patch('dbentry.base.admin.make_widget') as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = []
                # noinspection PyTypeChecker
                inline.formfield_for_foreignkey(
                    db_field=self.DummyModelField(), request=None, widget=object
                )
                make_mock.assert_not_called()


class MIZModelAdminTest(AdminTestCase):
    model_admin_class = TestAdmin
    model = Audio

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model)
        super().setUpTestData()

    def test_check_fieldset_fields(self):
        """Assert that _check_fieldset_fields finds invalid field declarations."""
        with patch.object(self.model_admin, 'fieldsets'):
            # Should ignore an empty fieldsets attribute or fieldsets without a
            # 'fields' item:
            self.model_admin.fieldsets = None
            self.assertFalse(self.model_admin._check_fieldset_fields())
            self.model_admin.fieldsets = [('name', {'no_fields': 'item'})]
            self.assertFalse(self.model_admin._check_fieldset_fields())

            # 'titel' is a valid field:
            self.model_admin.fieldsets = [(None, {'fields': ['titel']})]
            self.assertFalse(self.model_admin._check_fieldset_fields())

            # Now use a field that doesn't exist:
            self.model_admin.fieldsets = [
                (None, {'fields': ['titel', 'this_is_no_field']})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                "fieldset 'None' contains invalid item: 'this_is_no_field'. "
                "Audio has no field named 'this_is_no_field'"
            )

            # And an invalid lookup:
            self.model_admin.fieldsets = [(None, {'fields': ['titel__beep']})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                "fieldset 'None' contains invalid item: 'titel__beep'. "
                "Invalid lookup: beep for CharField."
            )

            # Also check in the case when a field is actually a tuple
            # (which would be a 'forward pair' for dal):
            self.model_admin.fieldsets = [
                (None, {'fields': [('titel', 'tracks')]})]
            self.assertFalse(self.model_admin._check_fieldset_fields())
            self.model_admin.fieldsets = [
                ('Beep', {'fields': [('titel', 'this_is_no_field')]})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                "fieldset 'Beep' contains invalid item: '('titel', 'this_is_no_field')'. "
                "Audio has no field named 'this_is_no_field'"
            )

    def test_get_queryset(self):
        """Assert that annotations are added to the model admin queryset."""
        request = self.get_request()
        with mock.patch.object(self.model_admin, 'get_changelist_annotations') as m:
            m.return_value = {}
            self.assertFalse(self.model_admin.get_queryset(request).query.annotations)
            m.return_value = {'c': Count('pk')}
            self.assertIn('c', self.model_admin.get_queryset(request).query.annotations)

    def test_get_index_category(self):
        self.assertEqual(self.model_admin.get_index_category(), 'Sonstige')  # default value
        self.model_admin.index_category = 'Hovercrafts'
        self.assertEqual(self.model_admin.get_index_category(), 'Hovercrafts')

    def test_has_merge_permission(self):
        ct = ContentType.objects.get_for_model(self.model)
        # noinspection PyUnresolvedReferences
        codename = get_permission_codename('merge', self.model._meta)
        perm = Permission.objects.create(
            name='Can merge Audio Material', content_type=ct, codename=codename
        )
        self.staff_user.user_permissions.add(perm)

        request = RequestFactory().get('/')
        request.user = self.noperms_user
        self.assertFalse(self.model_admin.has_merge_permission(request))
        request.user = self.staff_user
        self.assertTrue(self.model_admin.has_merge_permission(request))
        request.user = self.super_user
        self.assertTrue(self.model_admin.has_merge_permission(request))

    def test_has_alter_bestand_permission(self):
        perms = []
        for action in ('add', 'change', 'delete'):
            ct = ContentType.objects.get_for_model(Bestand)
            # noinspection PyUnresolvedReferences
            codename = get_permission_codename(action, Bestand._meta)
            perms.append(Permission.objects.get(codename=codename, content_type=ct))

        self.staff_user.user_permissions.add(*perms)

        request = RequestFactory().get('/')
        with patch('dbentry.base.admin.BESTAND_MODEL_NAME', 'tests.Bestand'):
            request.user = self.noperms_user
            self.assertFalse(self.model_admin.has_alter_bestand_permission(request))
            request.user = self.staff_user
            self.assertTrue(self.model_admin.has_alter_bestand_permission(request))
            request.user = self.super_user
            self.assertTrue(self.model_admin.has_alter_bestand_permission(request))

    def test_get_exclude(self):
        """
        get_exclude should add any concrete M2M field to the exclusion list,
        unless the ModelAdmin specifies exclude.
        """
        # tests.Veranstaltung has two concrete M2M fields and one 'reverse' M2M
        # field to Audio.
        model_admin = self.model_admin_class(Veranstaltung, self.admin_site)
        request = RequestFactory().get('/')
        excluded = model_admin.get_exclude(request)
        self.assertIn('musiker', excluded)
        self.assertIn('band', excluded)
        self.assertNotIn('audio', excluded)

        # Explicit exclude should take priority:
        model_admin.exclude = ['audio']
        excluded = model_admin.get_exclude(request)
        self.assertNotIn('musiker', excluded)
        self.assertNotIn('band', excluded)
        self.assertIn('audio', excluded)

    # TODO: @work: start here
    def test_add_bb_fieldset(self):
        self.fail("WRITE ME")

    def test_add_crosslinks(self):
        self.fail("WRITE ME")

    def test_add_extra_context(self):
        """Assert that add_extra_context adds additional items for the context."""
        for object_id in ('', self.obj.pk):
            with self.subTest(object_id=object_id):
                extra = self.model_admin.add_extra_context(object_id=object_id)
                self.assertIn('collapse_all', extra)
                if object_id:
                    self.assertIn('crosslinks', extra)
                else:
                    self.assertNotIn('crosslinks', extra)

    def test_add_view(self):
        """add_view context should include 'collapse_all' but not 'crosslinks'."""
        response = self.client.get(self.add_path)
        self.assertIn('collapse_all', response.context)
        self.assertNotIn('crosslinks', response.context, msg='no crosslinks allowed in add views')

    def test_change_view(self):
        """add_view context should include 'collapse_all' and 'crosslinks'."""
        response = self.client.get(self.change_path.format(pk=self.obj.pk))
        self.assertIn('collapse_all', response.context)
        self.assertIn('crosslinks', response.context)

    def test_save_model(self):
        """save_model should not update the _name of a ComputedNameModel object."""
        obj = make(Person, vorname='Alice', nachname='Testman')
        obj.nachname = 'Mantest'
        self.model_admin.save_model(None, obj, None, None)
        self.assertEqual(
            list(Person.objects.filter(pk=obj.pk).values_list('_name', flat=True)),
            ['Alice Testman']
        )

    def test_save_related(self):
        """
        save_related should force an update of the _name of a ComputedNameModel
        object.
        """
        obj = make(Person, vorname='Alice', nachname='Testman')
        obj.nachname = 'Mantest'
        # noinspection PyArgumentList
        obj.save(update=False)
        form = mock.Mock(instance=obj)
        with mock.patch('dbentry.base.admin.super'):
            self.model_admin.save_related(None, form, [], None)

        self.assertEqual(form.instance._name, 'Alice Mantest')
        self.assertEqual(
            list(Person.objects.filter(pk=obj.pk).values_list('_name', flat=True)),
            ['Alice Mantest']
        )

    def test_change_message_capitalized_fields(self):
        """Assert that the LogEntry/history change message uses the field labels."""
        form_class = self.model_admin.get_form(self.get_request(), obj=self.obj, change=True)
        form = form_class(data={'titel': 'A different title', 'tracks': '10'}, instance=self.obj)
        change_messages = self.model_admin.construct_change_message(
            request=None, form=form, formsets=None
        )

        self.assertIn('changed', change_messages[0])
        self.assertIn('fields', change_messages[0]['changed'])
        changed_fields = change_messages[0]['changed']['fields']
        for field in ('Titel', 'Anz. Tracks'):
            with self.subTest(field=field):
                self.assertIn(field, changed_fields)

    def test_get_search_results(self):
        self.fail("WRITE ME")
