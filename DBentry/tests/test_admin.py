import re
from unittest import skip
from unittest.mock import patch, Mock

from django.db import connections, transaction
from django.contrib import admin, contenttypes
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import User, Permission
from django.core import checks
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.translation import override as translation_override


import DBentry.admin as _admin
import DBentry.models as _models
from DBentry.changelist import MIZChangeList, AusgabeChangeList
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID
from DBentry.factory import make, modelfactory_factory
from DBentry.sites import miz_site
from DBentry.tests.base import AdminTestCase, TestCase
from DBentry.utils import get_model_fields


class AdminTestMethodsMixin(object):

    test_data_count = 1
    # the model instance with which the add_crosslinks method is to be tested
    crosslinks_object = None
    # the data used to create the crosslinks_object with (via make())
    crosslinks_object_data = None
    # the labels that the model_admin_class creates the crosslinks with
    crosslinks_labels = None
    # the data that is expected to be returned by add_crosslinks
    crosslinks_expected = []
    # fields to be excluded from the changeview form
    exclude_expected = None
    # fields expected to be on the changeview form
    fields_expected = None
    # the final search_fields expected
    search_fields_expected = None
    # if True, check the load order of jquery, select2 and django's jquery_init
    add_page_uses_select2 = True
    changelist_uses_select2 = True

    @classmethod
    def setUpTestData(cls):
        cls.visitor_user = User.objects.create_user(
            username='visitor', password='besucher', is_staff=True)
        p = Permission.objects.get(codename='view_%s' % cls.model._meta.model_name)
        cls.visitor_user.user_permissions.add(p)
        super().setUpTestData()
        if not cls.crosslinks_object:
            if cls.crosslinks_object_data:
                cls.crosslinks_object = make(cls.model, **cls.crosslinks_object_data)
            else:
                cls.crosslinks_object = modelfactory_factory(cls.model).full_relations()

    def get_crosslinks(self, obj, labels=None):
        # Return the crosslinks bit of the 'new_extra' context the model_admin would add.
        labels = labels or self.crosslinks_labels or self.model_admin.crosslink_labels or {}
        return self.model_admin.add_crosslinks(
            object_id=obj.pk, labels=labels).get('crosslinks')

    def _prepare_crosslink_data(self, data, obj=None):
        # Return a dict based off of 'data' similar in structure of those in the crosslinks.
        if obj is not None and 'pk' not in data:
            data['pk'] = str(obj.pk)
        if 'url' in data:
            url = data['url']
        else:
            url = '/admin/DBentry/{model_name}/?{fld_name}={pk}'.format(**data)
        return {'url': url, 'label': data['label']}

    def assertInCrosslinks(self, expected, links):
        # Assert that the data given in 'expected' is found in iterable 'links'.
        # Add an url entry to that data if necessary.
        if 'url' in expected:
            url = expected['url']
        else:
            url = '/admin/DBentry/{model_name}/?{fld_name}={pk}'.format(**expected)
        data = {'url': url, 'label': expected['label']}
        self.assertIn(data, links)
        return data

    def assertAllCrosslinks(self, obj, expected, links=None, labels=None):
        # A crosslink will link to a changelist page of the related model with
        # the related field filtered to the related object at hand.
        # For any relation given in crosslinks_relations check the existence and
        # correctness of the url & label provided by model_admin.add_crosslinks.
        # expected must be an iterable of dicts with the keys model_name,
        # fld_name and label.
        if links is None:
            links = self.get_crosslinks(obj, labels)
        _links = links.copy()

        # Check if any expected crosslinks are missing and remove found expected
        # crosslinks from 'links'.
        links_missing = []
        for item in expected:
            data = self._prepare_crosslink_data(item, obj)
            try:
                self.assertInCrosslinks(data, links)
            except AssertionError:
                links_missing.append(data)
            else:
                links.remove(data)
        if links_missing:
            sorting_key = lambda data: data['url']
            fail_message = 'The following crosslinks were not found:\n'
            fail_message += '\n'.join(str(l) for l in sorted(links_missing, key=sorting_key))
            fail_message += '\nCrosslinks available:\n'
            fail_message += '\n'.join(str(l) for l in sorted(_links, key=sorting_key))
            fail_message = (
                'The following crosslinks were not found:\n{missing}\n'
                'Crosslinks available:\n{links}'
            ).format(
                missing='\n'.join(str(l) for l in sorted(links_missing, key=sorting_key)),
                links='\n'.join(str(l) for l in sorted(_links, key=sorting_key))
            )
            self.fail(fail_message)
        if links:
            # There are some crosslinks left that were not expected:
            # check for any links that should not be in crosslinks because their
            # model is in inlines already.
            inline_crosslinks = []
            inline_model_names = [
                inline.model._meta.model_name for inline in self.model_admin.inlines]
            for i, link in enumerate(links.copy()):
                model_name_regex = re.search(r'DBentry/(\w+)/', link['url'])
                if not model_name_regex:
                    continue
                model_name = model_name_regex.groups()[0]
                if model_name in inline_model_names:
                    inline_crosslinks.append((model_name, links.pop(i)))

            fail_message = ''
            if inline_crosslinks:
                fail_message = (
                    'The following crosslinks were added despite their model '
                    'being present in the inlines already:\n{}'
                ).format('\n'.join(str(i) for i in inline_crosslinks))
            if links:
                # If there are still links left, then the test was not supplied
                # with the full expected data.
                if fail_message:
                    fail_message += '~' * 20
                fail_message = (
                    'The following crosslinks were added but no test data was '
                    'supplied or the inline is missing:\n{}'
                ).format('\n'.join(str(i) for i in links))
            if fail_message:
                self.fail(fail_message)

    def test_add_crosslinks(self):
        if self.crosslinks_object and self.crosslinks_expected is not None:
            self.assertAllCrosslinks(
                self.crosslinks_object, self.crosslinks_expected)
        else:
            warning = 'Poorly configured TestCase:'
            if not self.crosslinks_object:
                warning += ' No crosslinks_object supplied.'
            if self.crosslinks_expected is None:
                warning += ' No crosslinks_expected supplied.'
            self.warn(warning)

    def test_get_exclude(self):
        expected = []
        if self.exclude_expected:
            expected = sorted(self.exclude_expected)
        self.assertEqual(sorted(self.model_admin.get_exclude(self.get_request())), expected)

    def test_get_fields(self):
        expected = self.fields_expected or []
        self.assertEqual(self.model_admin.get_fields(self.get_request()), expected)

    def test_get_fieldsets(self):
        # Test that commentary fields are put into their own little fieldset,
        # unless the ModelAdmin class specifies fieldsets.
        fields = self.model_admin.get_fields(self.get_request())
        if (not self.model_admin_class.fieldsets
                and ('beschreibung' in fields or 'bemerkungen' in fields)):
            fieldsets = self.model_admin.get_fieldsets(self.get_request())
            self.assertIn(
                'Beschreibung & Bemerkungen', [fieldset[0] for fieldset in fieldsets])

    def test_formfield_for_foreignkey(self):
        # Test that every ForeignKey formfield gets a fancy select2 widget
        from DBentry.ac.widgets import MIZModelSelect2
        model_fields = get_model_fields(
            self.model, base=False, foreign=True, m2m=False)
        for fkey_field in model_fields:
            formfield = self.model_admin.formfield_for_foreignkey(
                fkey_field, self.get_request())
            self.assertIsInstance(
                formfield.widget, MIZModelSelect2, msg=fkey_field.name)

    def test_get_changelist(self):
        # TODO: wtf is this testing?
        request = self.get_request(path=self.changelist_path)
        self.assertEqual(self.model_admin.get_changelist(request), MIZChangeList)

    def test_get_search_fields(self):
        if self.search_fields_expected is None:
            return
        self.assertEqual(
            self.model_admin.get_search_fields(), self.search_fields_expected)

    @patch.object(admin.ModelAdmin, 'render_change_form')
    def test_changeform_media_context_collapse_after_jquery(self, mock):
        # Assert that a ModelAdmin's add/changeform loads jquery before collapse.
        # If the ModelAdmin does not contain any inlines the resulting media is
        # media + AdminForm.media, where AdminForm.media has collapse in between
        # jquery_base and jquery_init, ruining the load order.
        # InlineFormsets usually do not contain collapse (or at least there's
        # always one without it) so after media + InlineFormset.media jquery_init
        # follows directly after jquery_base.
        # Patch render_change_form to get at the context the mock is called with.
        try:
            path = reverse(
                'admin:DBentry_{}_add'.format(self.model._meta.model_name))
            self.model_admin._changeform_view(
                request=self.get_request(path=path),
                object_id=None,
                form_url='',
                extra_context={}
            )
        except TypeError:
            # A response (string/bytes) is expected to be returned
            # by _changeform_view.
            pass
        self.assertTrue(mock.called)
        # context is the second positional argument to render_change_form:
        context = mock.call_args[0][1]
        self.assertIn('media', context)
        media = context['media']
        from django.conf import settings
        jquery_base = 'admin/js/vendor/jquery/jquery{!s}.js'.format(
            '' if settings.DEBUG else '.min')
        jquery_init = 'admin/js/jquery.init.js'
        collapse = 'admin/js/collapse%s.js' % ('' if settings.DEBUG else '.min')

        if collapse in media._js:
            self.assertIn(jquery_base, media._js)
            self.assertIn(jquery_init, media._js)
            self.assertGreater(
                media._js.index(collapse),
                media._js.index(jquery_init),
                msg="jquery.init must be loaded before collapse.js"
            )
            self.assertGreater(
                media._js.index(jquery_init),
                media._js.index(jquery_base),
                msg="jquery base must be loaded before jquery.init"
            )

    def test_changelist_queries(self):
        # Assert that the number of queries needed for the changelist remains
        # constant and doesn't depend on the number of records fetched.
        # (which points to an unoptimized query / no prefetch)
        with CaptureQueriesContext(connections['default']) as queries:
            self.client.get(self.changelist_path)
        n = len(queries.captured_queries)
        make(self.model)
        with CaptureQueriesContext(connections['default']) as queries:
            self.client.get(self.changelist_path)
        self.assertEqual(
            n, len(queries.captured_queries),
            msg="Number of queries for changelist depends on number of records!"
        )

    def test_javascript_add_page(self):
        if self.add_page_uses_select2:
            with self.settings(DEBUG=True):
                response = self.get_response('GET', self.add_path)
                self.assertSelect2JS(response.context['media']._js)

    def test_javascript_change_list(self):
        if self.changelist_uses_select2:
            with self.settings(DEBUG=True):
                response = self.get_response('GET', self.changelist_path)
                self.assertSelect2JS(response.context['media']._js)

    def test_search(self):
        with self.assertNotRaises(Exception):
            response = self.client.get(
                self.changelist_path, data={admin.views.main.SEARCH_VAR:'Stuff'})
            self.assertEqual(response.status_code, 200)

    def test_changeform_availability(self):
        # Assert that the changeform is available.
        response = self.client.get(path=self.change_path.format(pk=self.obj1.pk))
        self.assertEqual(response.status_code, 200)

    def test_changeform_availability_view_only(self):
        # Assert that the changeform is available for user with 'view' only
        # permissions (like a visitor).
        self.client.force_login(self.visitor_user)
        response = self.client.get(path=self.change_path.format(pk=self.obj1.pk))
        self.assertEqual(response.status_code, 200)


class TestMIZModelAdmin(AdminTestCase):

    model_admin_class = _admin.DateiAdmin
    model = _models.Datei
    test_data_count = 1

    def test_has_merge_permission(self):
        codename = get_permission_codename('merge', self.model._meta)
        self.staff_user.user_permissions.add(
            Permission.objects.get(codename=codename))
        self.assertFalse(
            self.model_admin.has_merge_permission(
                request=self.get_request(user=self.noperms_user))
        )
        self.assertTrue(
            self.model_admin.has_merge_permission(
                request=self.get_request(user=self.staff_user))
        )
        self.assertTrue(
            self.model_admin.has_merge_permission(
                request=self.get_request(user=self.super_user))
        )

    def test_has_alter_bestand_permission(self):
        # Note: _models.Datei._meta doesn't set 'alter_bestand_datei' permission
        model_admin = _admin.VideoAdmin(_models.Video, self.admin_site)
        codename = get_permission_codename('alter_bestand', _models.Video._meta)
        self.staff_user.user_permissions.add(
            Permission.objects.get(codename=codename))
        self.assertFalse(
            model_admin.has_alter_bestand_permission(
                request=self.get_request(user=self.noperms_user))
        )
        self.assertTrue(
            model_admin.has_alter_bestand_permission(
                request=self.get_request(user=self.staff_user))
        )
        self.assertTrue(
            model_admin.has_alter_bestand_permission(
                request=self.get_request(user=self.super_user))
        )

    def test_add_extra_context(self):
        # No object_id passed in: add_crosslinks should not be called.
        extra = self.model_admin.add_extra_context()
        self.assertFalse('crosslinks' in extra)

    def test_add_view(self):
        response = self.client.get(self.add_path)
        self.assertTrue('collapse_all' in response.context)
        self.assertFalse(
            'crosslinks' in response.context,
            msg='no crosslinks allowed in add views'
        )

    def test_change_view(self):
        response = self.client.get(self.change_path.format(pk=self.obj1.pk))
        self.assertTrue('collapse_all' in response.context)
        self.assertTrue('crosslinks' in response.context)

    def test_get_changeform_initial_data_no_initial(self):
        request = self.get_request()
        self.assertEqual(self.model_admin.get_changeform_initial_data(request), {})

    def test_get_change_message_dict(self):
        # auto created
        obj = self.model.band.through.objects.create(
            band=_models.Band.objects.create(band_name='Testband'),
            datei=self.obj1
        )
        expected = {'name': 'Band', 'object': 'Testband'}
        self.assertEqual(
            self.model_admin._get_m2m_change_message_dict(obj), expected)

        # not auto created
        obj = self.model.musiker.through.objects.create(
            musiker=_models.Musiker.objects.create(kuenstler_name='Testmusiker'),
            datei=self.obj1
        )
        expected = {'name': 'Musiker', 'object': 'Testmusiker'}
        self.assertEqual(
            self.model_admin._get_m2m_change_message_dict(obj), expected)

    def test_save_model(self):
        # save_model should not update the _name of a ComputedNameModel object.
        obj = make(_models.Person, vorname='Alice', nachname='Testman')
        obj.nachname = 'Mantest'
        self.model_admin.save_model(None, obj, None, None)
        obj_queryset = _models.Person.objects.filter(pk=obj.pk)
        self.assertEqual(
            list(obj_queryset.values_list('_name', flat=True)),
            ['Alice Testman']
        )

    def test_save_related(self):
        # save_related should for an update of the _name of a ComputedNameModel
        # object.
        obj = make(_models.Person, vorname='Alice', nachname='Testman')
        obj.nachname = 'Mantest'
        obj.save(update=False)
        fake_form = type(
            'Dummy', (object, ), {'instance': obj, 'save_m2m': lambda x=None: None})
        self.model_admin.save_related(None, fake_form, [], None)
        self.assertEqual(fake_form.instance._name, 'Alice Mantest')
        self.assertEqual(
            list(_models.Person.objects.filter(pk=obj.pk).values_list('_name', flat=True)),
            ['Alice Mantest']
        )

    def test_add_pk_search_field(self):
        # Assert that a search field for the primary key is added to the search fields.
        # For primary keys that are a relation (OneToOneRelation) this should be
        # 'pk__pk__iexact' as 'iexact' is not a valid lookup for a OneToOneField.
        test_data = [
            ('NoRelation', self.model_admin, 'pk__iexact'),
            (
                'OneToOneRelation',
                _admin.KatalogAdmin(_models.Katalog, self.admin_site),
                'pk__pk__iexact'
            )
        ]
        mocked_has_search_form = Mock(return_value=False)
        for test_desc, model_admin, expected in test_data:
            with patch.object(model_admin, 'has_search_form', new=mocked_has_search_form):
                with self.subTest(desc=test_desc):
                    search_fields = model_admin._add_pk_search_field([])
                    self.assertTrue(search_fields, msg="Expected pk field to be added.")
                    self.assertEqual(
                        len(search_fields), 1,
                        msg="Only one pk search field expected. Got: %s" % str(search_fields)
                    )
                    self.assertIn(expected, search_fields)

    def test_add_pk_search_field_does_not_overwrite_existing(self):
        # Assert that _add_pk_search_field does not overwrite or delete
        # existing primary key search_fields.
        pk_name = self.model._meta.pk.name
        test_data = [
            ('no prefix', ['pk']),
            ('prefixed', ['=pk']),
            ('lookup', ['pk__istartswith']),
            ('lookup prefixed', ['=pk__istartswith']),
            ('pk name', [pk_name]),
            ('pk name prefixed', ['=%s' % pk_name]),
            ('pk name lookup', ['%s__istartswith' % pk_name]),
            ('pk name lookup prefixed', ['=%s__istartswith' % pk_name])
        ]

        for test_desc, initial_fields in test_data:
            with self.subTest(desc=test_desc):
                search_fields = self.model_admin._add_pk_search_field(initial_fields)
                self.assertEqual(initial_fields, search_fields)

    def test_add_pk_search_field_with_search_form(self):
        # Assert that _add_pk_search_field only adds a pk search field if the
        # model admin does NOT have a search form.
        with patch.object(self.model_admin, 'has_search_form') as mocked_has_search_form:
            mocked_has_search_form.return_value = False
            search_fields = self.model_admin._add_pk_search_field([])
            self.assertTrue(
                search_fields,
                msg="ModelAdmin instances without a search_form should add a"
                    "primary key search field."
            )
            mocked_has_search_form.return_value = True
            search_fields = self.model_admin._add_pk_search_field([])
            self.assertFalse(
                search_fields,
                msg="ModelAdmin instances with a search_form should not add a "
                    "primary key search field."
            )

    def test_change_message_capitalized_fields(self):
        # Assert that the LogEntry/history change message uses the field labels.
        model_admin = _admin.ArtikelAdmin(_models.Artikel, miz_site)
        obj = make(_models.Artikel)
        form_class = model_admin.get_form(self.get_request(), obj=obj, change=True)
        form = form_class(data={}, instance=obj)
        change_message = model_admin.construct_change_message(
            request=None, form=form, formsets=None)[0]

        self.assertIn('changed', change_message)
        self.assertIn('fields', change_message['changed'])
        changed_fields = change_message['changed']['fields']
        for field in ('Ausgabe', 'Magazin'):
            with self.subTest(field=field):
                self.assertIn(field, changed_fields)

    def test_check_list_prefetch_related(self):
        # Assert that check_list_prefetch_related returns an empty list if the
        # class attribute 'list_prefetch_related' is unset or None.
        self.assertEqual(
            # object obviously doesn't have the attribute:
            self.model_admin_class._check_list_prefetch_related(object), [])
        with patch.object(self.model_admin, 'list_prefetch_related', new=None, create=True):
            self.assertEqual(self.model_admin._check_list_prefetch_related(), [])
            # list_prefetch_related must be a list or tuple:
            self.model_admin.list_prefetch_related = 'Not a list!'
            checked = self.model_admin._check_list_prefetch_related()
            self.assertEqual(len(checked), 1)
            self.assertIsInstance(checked[0], checks.Error)
            self.assertEqual(
                checked[0].msg,
                "{}.list_prefetch_related attribute must be a list or a tuple.".format(
                    self.model_admin_class.__name__)
            )
            self.model_admin.list_prefetch_related = []
            self.assertFalse(self.model_admin._check_list_prefetch_related())
            self.model_admin.list_prefetch_related = ()
            self.assertFalse(self.model_admin._check_list_prefetch_related())
            # Every item in list_prefetch_related must be an attribute of the
            # ModelAdmin's model.
            self.model_admin.list_prefetch_related = [
                'musiker', 'musiker_set', 'band', 'band_set']
            checked = self.model_admin._check_list_prefetch_related()
            self.assertEqual(len(checked), 2)
            msg_template = (
                "Invalid item in {model_admin}.list_prefetch_related: "
                "cannot find '{field_name}' on model {object_name}"
            )
            template_kwargs = {
                'model_admin': self.model_admin_class.__name__,
                'object_name': self.model._meta.object_name
            }
            self.assertIsInstance(checked[0], checks.Error)
            self.assertEqual(
                checked[0].msg,
                msg_template.format(field_name='musiker_set', **template_kwargs)
            )
            self.assertIsInstance(checked[1], checks.Error)
            self.assertEqual(
                checked[1].msg,
                msg_template.format(field_name='band_set', **template_kwargs)
            )

    def test_check_fieldset_fields(self):
        # Assert that _check_fieldset_fields finds invalid field declarations.
        with patch.object(self.model_admin, 'fieldsets'):
            # Should ignore an empty fieldsets attribute or fieldsets without a
            # 'fields' item:
            self.model_admin.fieldsets = None
            self.assertFalse(self.model_admin._check_fieldset_fields())
            self.model_admin.fieldsets = [('name', {'nofields': 'item'})]
            self.assertFalse(self.model_admin._check_fieldset_fields())
            # 'titel' is a valid field:
            self.model_admin.fieldsets = [(None, {'fields': ['titel']})]
            self.assertFalse(self.model_admin._check_fieldset_fields())
            # Now use a field that doesn't exist:
            msg_template = "fieldset '%s' contains invalid item: '%s'. %s"
            self.model_admin.fieldsets = [(None, {'fields': ['titel', 'thisisnofield']})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                msg_template % (
                    'None', 'thisisnofield', "Datei has no field named 'thisisnofield'"
                )
            )
            # And an invalid lookup:
            self.model_admin.fieldsets = [(None, {'fields': ['titel__beep']})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                msg_template % (
                    'None', 'titel__beep', "Invalid lookup: beep for CharField."
                )
            )
            # Also check in the case when a field is actually a tuple
            # (which would be a 'forward pair' for dal):
            self.model_admin.fieldsets = [(None, {'fields': [('titel', 'media_typ')]})]
            self.assertFalse(self.model_admin._check_fieldset_fields())
            self.model_admin.fieldsets = [('Beep', {'fields': [('titel', 'thisisnofield')]})]
            errors = self.model_admin._check_fieldset_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg, msg_template % (
                    'Beep', ('titel', 'thisisnofield'), "Datei has no field named 'thisisnofield'"
                )
            )

    def test_check_search_fields_lookups(self):
        # Assert that _check_search_fields_lookups finds invalid search fields
        # and/or lookups correctly.
        with patch.object(self.model_admin, 'get_search_fields'):
            self.model_admin.get_search_fields.return_value = ['titel__iexact']
            self.assertFalse(self.model_admin._check_search_fields_lookups())
            # Check for invalid field:
            self.model_admin.get_search_fields.return_value = ['thisisnofield']
            errors = self.model_admin._check_search_fields_lookups()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                "Invalid search field '{0}': {1} has no field named '{0}'".format(
                    'thisisnofield', self.model._meta.object_name)
            )
            # Check for invalid lookups:
            self.model_admin.get_search_fields.return_value = ['genre__genre__year']
            errors = self.model_admin._check_search_fields_lookups()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                "Invalid search field '%s': Invalid lookup: %s for %s." % (
                    'genre__genre__year', 'year', 'CharField')
            )

    def test_check_search_fields_lookups_lookup_shortcuts(self):
        # Assert that _check_search_fields_lookups handles lookup shortcuts
        # such as '=', '^', '@' (for django's ModelAdmin.construct_search).
        # Check each valid prefix twice: once with a valid field and once with
        # an invalid one. If only the invalid fields fail the check, the problem
        # can't be the prefix.
        msg_template = "Invalid search field '{0}': {1} has no field named '{0}'"
        with patch.object(self.model_admin, 'get_search_fields'):
            for prefix in ('=', '^', '@'):
                for invalid, field in enumerate(('titel', 'thisisnofield')):
                    self.model_admin.get_search_fields.return_value = [prefix + field]
                    with self.subTest(prefix=prefix, field=field):
                        if invalid:
                            errors = self.model_admin._check_search_fields_lookups()
                            self.assertTrue(errors)
                            self.assertEqual(len(errors), 1)
                            self.assertIsInstance(errors[0], checks.Error)
                            expected_msg = msg_template.format(field, self.model._meta.object_name)
                            self.assertEqual(errors[0].msg, expected_msg)
                        else:
                            self.assertFalse(self.model_admin._check_search_fields_lookups())
            # Any other prefix should receive no special treatment:
            for field in ('_thisisnofield', '&nofieldeither'):
                with self.subTest(field=field):
                    self.model_admin.get_search_fields.return_value = [field]
                    errors = self.model_admin._check_search_fields_lookups()
                    self.assertTrue(errors)
                    self.assertEqual(len(errors), 1)
                    self.assertIsInstance(errors[0], checks.Error)
                    # The 'prefix' should be included in the error message.
                    expected_msg = msg_template.format(field, self.model._meta.object_name)
                    self.assertEqual(errors[0].msg, expected_msg)

    @patch("DBentry.base.admin.resolve_list_display_item")
    def test_check_list_item_annotations(self, mocked_resolve):
        # Assert that _check_list_item_annotations checks that annotations
        # declared on a list_display item are Aggregations.
        with patch.object(self.model_admin, 'list_display'):
            # First: some special conditions where _check_list_item_annotations
            # just continues looping through the list_display items.
            # resolve_list_display_item could not resolve the item and
            # returned None:
            self.model_admin.list_display = ['thisisnofield']
            mocked_resolve.return_value = None
            self.assertFalse(self.model_admin._check_list_item_annotations())
            # The func returned by resolve_list_display_item does not have
            # a 'admin_order_field' attribute:
            some_func = lambda x: x
            mocked_resolve.return_value = some_func
            self.assertFalse(self.model_admin._check_list_item_annotations())
            # The func returned by resolve_list_display_item does not have
            # a 'annotations' attribute.
            setattr(some_func, 'admin_order_field', 'beep')
            self.assertFalse(self.model_admin._check_list_item_annotations())
            # Add an invalid 'annotation' attribute to our dummy func:
            setattr(some_func, 'annotation', 'not_an_aggregate_instance')
            expected_msg = "%s.%s.annotation is not an aggregate: %s" % (
                    self.model_admin_class.__name__, some_func.__name__, type(''))
            errors = self.model_admin._check_list_item_annotations()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(errors[0].msg, expected_msg)


class TestArtikelAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.ArtikelAdmin
    model = _models.Artikel
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'autor', 'band', 'musiker', 'ort',
        'spielort', 'veranstaltung'
    ]
    fields_expected = [
        ('ausgabe__magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'),
        'zusammenfassung', 'beschreibung', 'bemerkungen'
    ]
    search_fields_expected = ['schlagzeile', 'zusammenfassung', 'beschreibung', 'bemerkungen']

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.obj1 = make(
            _models.Artikel, ausgabe__magazin=cls.mag, seite=1, schlagzeile='Test!',
            schlagwort__schlagwort=['Testschlagwort1', 'Testschlagwort2'],
            musiker__kuenstler_name='Alice Tester', band__band_name='Testband'
        )
        cls.test_data = [cls.obj1]

        super().setUpTestData()

    def test_zusammenfassung_string(self):
        self.assertEqual(self.model_admin.zusammenfassung_string(self.obj1), '')
        self.obj1.zusammenfassung = (
            "Dies ist eine Testzusammenfassung, die nicht besonders inhaltsvoll "
            "ist, dafür aber doch recht lang ist."
        )
        self.assertEqual(
            self.model_admin.zusammenfassung_string(self.obj1),
            "Dies ist eine Testzusammenfassung, die nicht besonders inhaltsvoll "
            "ist, dafür aber doch recht lang [...]"
        )

    def test_artikel_magazin(self):
        self.assertEqual(self.model_admin.artikel_magazin(self.obj1), self.mag)

    def test_schlagwort_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(
            self.model_admin.schlagwort_string(obj),
            'Testschlagwort1, Testschlagwort2'
        )

    def test_kuenstler_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(
            self.model_admin.kuenstler_string(obj),
            'Testband, Alice Tester'
        )


class TestAusgabenAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.AusgabenAdmin
    model = _models.Ausgabe
    exclude_expected = ['audio']
    fields_expected = [
        'magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang',
        'beschreibung', 'bemerkungen'
    ]
    search_fields_expected = ['_name', 'beschreibung', 'bemerkungen']
    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'ausgabe', 'label': 'Artikel (1)'}]

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            _models.Ausgabe,
            magazin__magazin_name='Testmagazin',
            ausgabejahr__jahr=[2020, 2021, 2022],
            ausgabenum__num=[10, 11, 12],
            ausgabelnum__lnum=[10, 11, 12],
            ausgabemonat__monat__monat=['Januar', 'Februar'],
            artikel__schlagzeile='Test', artikel__seite=1,
            bestand__lagerort__pk=[ZRAUM_ID, DUPLETTEN_ID],
        )

        cls.test_data = [cls.obj1]

        super().setUpTestData()

    def test_get_changelist(self):
        self.assertEqual(
            self.model_admin.get_changelist(self.get_request()), AusgabeChangeList)

    def test_changelist_ordering(self):
        # Check that the changelist results are only chronologically ordered
        # when the ORDER_VAR ('o') is not present in the query string.
        request_data = {'magazin': self.obj1.magazin_id}
        request = self.get_request(data=request_data)
        queryset = self.model_admin.get_changelist_instance(request).get_queryset(request)
        self.assertTrue(queryset.chronologically_ordered)
        request_data[admin.views.main.ORDER_VAR] = '1'
        request = self.get_request(data=request_data)
        queryset = self.model_admin.get_changelist_instance(request).get_queryset(request)
        self.assertFalse(queryset.chronologically_ordered)

    def test_anz_artikel(self):
        obj = self.get_queryset().get(pk=self.obj1.pk)
        self.assertEqual(self.model_admin.anz_artikel(obj), 1)
        _models.Artikel.objects.all().delete()
        obj = self.get_queryset().get(pk=self.obj1.pk)
        self.assertEqual(self.model_admin.anz_artikel(obj), 0)

    def test_jahr_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(self.model_admin.jahr_string(obj), '2020, 2021, 2022')

    def test_num_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(self.model_admin.num_string(obj), '10, 11, 12')

    def test_lnum_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(self.model_admin.lnum_string(obj), '10, 11, 12')

    def test_monat_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(self.model_admin.monat_string(obj), 'Jan, Feb')

    def test_add_crosslinks_custom(self):
        obj = make(
            _models.Ausgabe,
            ausgabenum__extra=1, ausgabelnum__extra=1, ausgabemonat__extra=1,
            ausgabejahr__extra=1,
            artikel__extra=1, audio__extra=1, bestand__extra=1,
        )
        # Only artikel should show up in the crosslinks as audio is present in the inlines.
        links = self.get_crosslinks(obj)
        self.assertEqual(len(links), 1)
        expected = {
            'model_name': 'artikel', 'fld_name': 'ausgabe',
            'label': 'Artikel (1)', 'pk': str(obj.pk)
        }
        self.assertInCrosslinks(expected, links)

        links = self.get_crosslinks(obj, labels={'artikel': 'Beep boop'})
        expected = {
            'model_name': 'artikel', 'fld_name': 'ausgabe',
            'label': 'Beep boop (1)', 'pk': str(obj.pk)
        }
        self.assertInCrosslinks(expected, links)

        with patch.object(_models.Ausgabe.artikel_set.rel, 'related_name', new='Boop beep'):
            links = self.get_crosslinks(obj)
            expected = {
                'model_name': 'artikel', 'fld_name': 'ausgabe',
                'label': 'Boop Beep (1)', 'pk': str(obj.pk)
            }  # Note the capitalization of each starting letter!
            self.assertInCrosslinks(expected, links)

        obj.artikel_set.all().delete()
        self.assertFalse(self.get_crosslinks(obj))

    def test_actions_noperms(self):
        # Assert that certain actions are not available to user without permissions.
        actions = self.model_admin.get_actions(self.get_request(user=self.noperms_user))
        action_names = (
            'bulk_jg', 'add_bestand', 'moveto_brochure', 'merge_records',
            'change_status_unbearbeitet', 'change_status_inbearbeitung',
            'change_status_abgeschlossen'
        )
        for action_name in action_names:
            with self.subTest(action_name=action_name):
                self.assertNotIn(action_name, actions)

    def test_actions_staff_user(self):
        # Assert that certain actions are available for staff users with the
        # proper permissions.
        for perm_name in ('change', 'alter_bestand', 'delete', 'merge'):
            # bulk_jg requires 'change' and moveto_brochure requires 'delete'
            codename = get_permission_codename(perm_name, self.model._meta)
            self.staff_user.user_permissions.add(
                Permission.objects.get(codename=codename))
        actions = self.model_admin.get_actions(self.get_request(user=self.staff_user))
        action_names = (
            'bulk_jg', 'add_bestand', 'merge_records',
            'change_status_unbearbeitet', 'change_status_inbearbeitung',
            'change_status_abgeschlossen'
        )
        for action_name in action_names:
            with self.subTest(action_name=action_name):
                self.assertIn(action_name, actions)

    def test_movetobrochure_permissions(self):
        # moveto_brochure should require both 'delete_ausgabe' and 'add_BaseBrochure'
        # permissions.
        msg_template = (
            "Action 'moveto_brochure' should not be available to "
            "users that miss the '%s' permission."
        )
        delete_codename = get_permission_codename('delete', _models.Ausgabe._meta)
        delete_permission = Permission.objects.get(codename=delete_codename)
        add_codename = get_permission_codename('add', _models.BaseBrochure._meta)
        add_permission = Permission.objects.get(codename=add_codename)

        # delete only: not allowed
        self.staff_user.user_permissions.set([delete_permission])
        request = self.get_request(user=self.staff_user)
        self.assertFalse(
            self.model_admin.has_moveto_brochure_permission(request),
            msg=msg_template % add_codename
        )

        # add only: not allowed
        self.staff_user.user_permissions.set([add_permission])
        request = self.get_request(user=self.staff_user)
        self.assertFalse(
            self.model_admin.has_moveto_brochure_permission(request),
            msg=msg_template % delete_codename
        )

        # delete + add: moveto_brochure allowed
        self.staff_user.user_permissions.set([delete_permission, add_permission])
        request = self.get_request(user=self.staff_user)
        self.assertTrue(
            self.model_admin.has_moveto_brochure_permission(request),
            msg=(
                "Action 'moveto_brochure' should be available for users with both "
                "'%s' and '%s' permissions" % (delete_codename, add_codename)
            )
        )

    def test_actions_super_user(self):
        # Assert that certain actions are available for super users.
        actions = self.model_admin.get_actions(self.get_request(user=self.super_user))
        action_names = (
            'bulk_jg', 'add_bestand', 'moveto_brochure', 'merge_records',
            'change_status_unbearbeitet', 'change_status_inbearbeitung',
            'change_status_abgeschlossen'
        )
        for action_name in action_names:
            with self.subTest(action_name=action_name):
                self.assertIn(action_name, actions)

    def test_brochure_crosslink(self):
        # Assert that crosslinks to all of the BaseBrochure children are displayed.
        # Do note that factory full_relations only creates one related object
        # instead of three for each BaseBrochure child.
        obj = make(self.model)
        make(_models.Brochure, ausgabe=obj)
        make(_models.Kalender, ausgabe=obj)
        make(_models.Katalog, ausgabe=obj)
        crosslinks = self.get_crosslinks(obj, labels={})
        data = {'fld_name': 'ausgabe', 'pk': str(obj.pk)}
        labels = {
            'brochure': 'Broschüren (1)',
            'kalender': 'Programmhefte (1)',
            'katalog': 'Warenkataloge (1)'
        }
        for model_name in ('brochure', 'kalender', 'katalog'):
            with self.subTest(model=model_name):
                data['model_name'] = model_name
                data['label'] = labels[model_name]
                self.assertInCrosslinks(data, crosslinks)

    def test_change_status_unbearbeitet(self):
        self.model_admin.change_status_unbearbeitet(self.get_request(), self.queryset)
        self.assertEqual(set(self.queryset.values_list('status', flat=True)), {'unb'})

    def test_change_status_inbearbeitung(self):
        self.model_admin.change_status_inbearbeitung(self.get_request(), self.queryset)
        self.assertEqual(set(self.queryset.values_list('status', flat=True)), {'iB'})

    def test_change_status_abgeschlossen(self):
        self.model_admin.change_status_abgeschlossen(self.get_request(), self.queryset)
        self.assertEqual(set(self.queryset.values_list('status', flat=True)), {'abg'})

    def test_change_status(self):
        # Integration test for the change_status stuff.
        for action, expected_value in [
                ('change_status_inbearbeitung', 'iB'),
                ('change_status_abgeschlossen', 'abg'),
                # obj1.status is 'unb' at the start, so test for 'unb' last to be
                # able to register a change:
                ('change_status_unbearbeitet', 'unb')
            ]:
            request_data = {
                'action': action,
                admin.helpers.ACTION_CHECKBOX_NAME: self.obj1.pk,
                'index': 0,  # required by changelist_view to identify the request as an action
            }
            path = self.changelist_path + '?magazin=%s' % self.obj1.magazin_id
            with self.subTest(action=action, status=expected_value):
                with transaction.atomic():
                    response = self.client.post(path, data=request_data)
                self.assertEqual(response.status_code, 302)
                self.obj1.refresh_from_db()
                self.assertEqual(self.obj1.status, expected_value)


class TestMagazinAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.MagazinAdmin
    model = _models.Magazin
    exclude_expected = ['genre', 'verlag', 'herausgeber', 'orte']
    fields_expected = [
        'magazin_name', 'ausgaben_merkmal', 'fanzine', 'issn',
        'beschreibung', 'bemerkungen',
    ]
    search_fields_expected = ['magazin_name', 'beschreibung', 'bemerkungen']

    crosslinks_expected = [
        {'model_name': 'ausgabe', 'fld_name': 'magazin', 'label': 'Ausgaben (1)'},
        {'model_name': 'autor', 'fld_name': 'magazin', 'label': 'Autoren (1)'}
    ]

    raw_data = [{'ausgabe__extra': 1}]

    def test_anz_ausgaben(self):
        obj = self.get_queryset().get(pk=self.obj1.pk)
        self.assertEqual(self.model_admin.anz_ausgaben(obj), 1)
        self.obj1.ausgabe_set.all().delete()
        obj = self.get_queryset().get(pk=self.obj1.pk)
        self.assertEqual(self.model_admin.anz_ausgaben(obj), 0)

    def test_ausgaben_merkmal_excluded(self):
        # Assert that field 'ausgaben_merkmal' is only included for superusers.
        codename = get_permission_codename('change', self.model._meta)
        self.staff_user.user_permissions.add(Permission.objects.get(codename=codename))
        request = Mock(user=self.staff_user)
        self.assertIn(
            'ausgaben_merkmal', self.model_admin.get_exclude(request),
            msg="Non-superuser users should not have access to field 'ausgaben_merkmal'."
        )
        request = Mock(user=self.super_user)
        self.assertNotIn(
            'ausgaben_merkmal', self.model_admin.get_exclude(request),
            msg="Superusers users should have access to field 'ausgaben_merkmal'."
        )


class TestPersonAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.PersonAdmin
    model = _models.Person
    exclude_expected = ['orte']
    fields_expected = ['vorname', 'nachname', 'beschreibung', 'bemerkungen']
    search_fields_expected = ['_name', 'beschreibung', 'bemerkungen']
    # one extra 'empty' object without relations for Ist_Autor/Ist_Musiker:
    test_data_count = 1

    raw_data = [
        {'musiker__extra': 1, 'autor__extra': 1},
    ]

    crosslinks_expected = [
        {'model_name': 'video', 'fld_name': 'person', 'label': 'Video Materialien (1)'},
        {'model_name': 'veranstaltung', 'fld_name': 'person', 'label': 'Veranstaltungen (1)'},
        {'model_name': 'datei', 'fld_name': 'person', 'label': 'Dateien (1)'},
        {'model_name': 'artikel', 'fld_name': 'person', 'label': 'Artikel (1)'},
        {'model_name': 'autor', 'fld_name': 'person', 'label': 'Autoren (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'person', 'label': 'Memorabilien (1)'},
        {'model_name': 'dokument', 'fld_name': 'person', 'label': 'Dokumente (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'person', 'label': 'Bild Materialien (1)'},
        {'model_name': 'technik', 'fld_name': 'person', 'label': 'Technik (1)'},
        {'model_name': 'audio', 'fld_name': 'person', 'label': 'Audio Materialien (1)'},
        {'model_name': 'buch', 'fld_name': 'person', 'label': 'Bücher (1)'},
        {'model_name': 'musiker', 'fld_name': 'person', 'label': 'Musiker (1)'},
    ]

    def test_Ist_Musiker(self):
        self.assertTrue(self.model_admin.Ist_Musiker(self.obj1))
        self.assertFalse(self.model_admin.Ist_Musiker(self.obj2))

    def test_Ist_Autor(self):
        self.assertTrue(self.model_admin.Ist_Autor(self.obj1))
        self.assertFalse(self.model_admin.Ist_Autor(self.obj2))

    def test_orte_string(self):
        self.assertEqual(self.model_admin.orte_string(self.obj1), '')
        o = make(_models.Ort, stadt='Dortmund', land__code='XYZ')
        self.obj1.orte.add(o)
        self.obj1.refresh_from_db()
        self.assertEqual(self.model_admin.orte_string(self.obj1), 'Dortmund, XYZ')


class TestMusikerAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.MusikerAdmin
    model = _models.Musiker
    test_data_count = 1
    exclude_expected = ['genre', 'instrument', 'orte']
    fields_expected = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    search_fields_expected = [
        'kuenstler_name', 'musikeralias__alias', 'person___name',
        'beschreibung', 'bemerkungen'
    ]

    raw_data = [
        {},
        {
            'band__band_name': ['Testband1', 'Testband2'],
            'genre__genre':['Testgenre1', 'Testgenre2']
        }
    ]

    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'musiker', 'label': 'Artikel (1)'},
        {'model_name': 'audio', 'fld_name': 'musiker', 'label': 'Audio Materialien (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'musiker', 'label': 'Bild Materialien (1)'},
        {'model_name': 'buch', 'fld_name': 'musiker', 'label': 'Bücher (1)'},
        {'model_name': 'datei', 'fld_name': 'musiker', 'label': 'Dateien (1)'},
        {'model_name': 'dokument', 'fld_name': 'musiker', 'label': 'Dokumente (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'musiker', 'label': 'Memorabilien (1)'},
        {'model_name': 'technik', 'fld_name': 'musiker', 'label': 'Technik (1)'},
        {'model_name': 'veranstaltung', 'fld_name': 'musiker', 'label': 'Veranstaltungen (1)'},
        {'model_name': 'video', 'fld_name': 'musiker', 'label': 'Video Materialien (1)'},
    ]

    def test_add_extra_context(self):
        extra = self.model_admin.add_extra_context(object_id=self.obj1.pk)
        self.assertTrue('crosslinks' in extra)

    def test_band_string(self):
        self.assertEqual(self.model_admin.band_string(self.obj2), 'Testband1, Testband2')

    def test_genre_string(self):
        self.assertEqual(self.model_admin.genre_string(self.obj2), 'Testgenre1, Testgenre2')

    def test_orte_string(self):
        self.assertEqual(self.model_admin.orte_string(self.obj2), '')
        o = make(_models.Ort, stadt='Dortmund', land__code='XYZ')
        self.obj2.orte.add(o)
        self.obj2.refresh_from_db()
        self.assertEqual(self.model_admin.orte_string(self.obj2), 'Dortmund, XYZ')


class TestGenreAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.GenreAdmin
    model = _models.Genre
    fields_expected = ['genre']
    search_fields_expected = ['genre', 'genrealias__alias', 'pk__iexact']
    add_page_uses_select2 = False
    changelist_uses_select2 = False

    raw_data = [
        {
            'genre': 'Subobject',
            'genrealias__alias': ['Alias1', 'Alias2'],
        }
    ]

    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'genre', 'label': 'Artikel (1)'},
        {'model_name': 'audio', 'fld_name': 'genre', 'label': 'Audio Materialien (1)'},
        {'model_name': 'band', 'fld_name': 'genre', 'label': 'Bands (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'genre', 'label': 'Bild Materialien (1)'},
        {'model_name': 'buch', 'fld_name': 'genre', 'label': 'Bücher (1)'},
        {'model_name': 'datei', 'fld_name': 'genre', 'label': 'Dateien (1)'},
        {'model_name': 'magazin', 'fld_name': 'genre', 'label': 'Magazine (1)'},
        {'model_name': 'dokument', 'fld_name': 'genre', 'label': 'Dokumente (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'genre', 'label': 'Memorabilien (1)'},
        {'model_name': 'musiker', 'fld_name': 'genre', 'label': 'Musiker (1)'},
        {'model_name': 'technik', 'fld_name': 'genre', 'label': 'Technik (1)'},
        {'model_name': 'veranstaltung', 'fld_name': 'genre', 'label': 'Veranstaltungen (1)'},
        {'model_name': 'video', 'fld_name': 'genre', 'label': 'Video Materialien (1)'},
    ]

    def test_alias_string(self):
        self.assertEqual(self.model_admin.alias_string(self.obj1), 'Alias1, Alias2')

    def test_brochure_crosslink(self):
        # Assert that crosslinks to all of the BaseBrochure children are displayed.
        # Do note that factory full_relations only creates one related object
        # instead of three for each BaseBrochure child.
        obj = make(self.model)
        make(_models.Brochure, genre=obj)
        make(_models.Kalender, genre=obj)
        make(_models.Katalog, genre=obj)
        crosslinks = self.get_crosslinks(obj, labels={})
        data = {'fld_name': 'genre', 'pk': str(obj.pk)}
        labels = {
            'brochure': 'Broschüren (1)',
            'kalender': 'Programmhefte (1)',
            'katalog': 'Warenkataloge (1)'
        }
        for model_name in ('brochure', 'kalender', 'katalog'):
            with self.subTest(model=model_name):
                data['model_name'] = model_name
                data['label'] = labels[model_name]
                self.assertInCrosslinks(data, crosslinks)


class TestSchlagwortAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.SchlagwortAdmin
    model = _models.Schlagwort
    fields_expected = ['schlagwort']
    search_fields_expected = ['schlagwort', 'schlagwortalias__alias', 'pk__iexact']
    add_page_uses_select2 = False
    changelist_uses_select2 = False

    raw_data = [
        {
            'schlagwort': 'Subobject',
            'schlagwortalias__alias': ['Alias1', 'Alias2'],
        }
    ]

    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'schlagwort', 'label': 'Artikel (1)'},
        {'model_name': 'audio', 'fld_name': 'schlagwort', 'label': 'Audio Materialien (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'schlagwort', 'label': 'Bild Materialien (1)'},
        {'model_name': 'brochure', 'fld_name': 'schlagwort', 'label': 'Broschüren (1)'},
        {'model_name': 'buch', 'fld_name': 'schlagwort', 'label': 'Bücher (1)'},
        {'model_name': 'datei', 'fld_name': 'schlagwort', 'label': 'Dateien (1)'},
        {'model_name': 'dokument', 'fld_name': 'schlagwort', 'label': 'Dokumente (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'schlagwort', 'label': 'Memorabilien (1)'},
        {'model_name': 'technik', 'fld_name': 'schlagwort', 'label': 'Technik (1)'},
        {'model_name': 'veranstaltung', 'fld_name': 'schlagwort', 'label': 'Veranstaltungen (1)'},
        {'model_name': 'video', 'fld_name': 'schlagwort', 'label': 'Video Materialien (1)'},
    ]

    def test_alias_string(self):
        self.assertEqual(self.model_admin.alias_string(self.obj1), 'Alias1, Alias2')


class TestBandAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.BandAdmin
    model = _models.Band
    exclude_expected = ['genre', 'musiker', 'orte']
    fields_expected = ['band_name', 'beschreibung', 'bemerkungen']
    search_fields_expected = ['band_name', 'bandalias__alias', 'beschreibung', 'bemerkungen']
    raw_data = [
        {
            'bandalias__alias': ['Alias1', 'Alias2'],
            'genre__genre': ['Testgenre1', 'Testgenre2'],
            'musiker__kuenstler_name': ['Testkuenstler1', 'Testkuenstler2']
        }
    ]

    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'band', 'label': 'Artikel (1)'},
        {'model_name': 'audio', 'fld_name': 'band', 'label': 'Audio Materialien (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'band', 'label': 'Bild Materialien (1)'},
        {'model_name': 'buch', 'fld_name': 'band', 'label': 'Bücher (1)'},
        {'model_name': 'datei', 'fld_name': 'band', 'label': 'Dateien (1)'},
        {'model_name': 'dokument', 'fld_name': 'band', 'label': 'Dokumente (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'band', 'label': 'Memorabilien (1)'},
        {'model_name': 'technik', 'fld_name': 'band', 'label': 'Technik (1)'},
        {'model_name': 'veranstaltung', 'fld_name': 'band', 'label': 'Veranstaltungen (1)'},
        {'model_name': 'video', 'fld_name': 'band', 'label': 'Video Materialien (1)'},
    ]

    def test_alias_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(self.model_admin.alias_string(obj), 'Alias1, Alias2')

    def test_genre_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(self.model_admin.genre_string(obj), 'Testgenre1, Testgenre2')

    def test_musiker_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(
            self.model_admin.musiker_string(obj),
            'Testkuenstler1, Testkuenstler2'
        )

    def test_orte_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(self.model_admin.orte_string(obj), '')
        o = make(_models.Ort, stadt='Dortmund', land__code='XYZ')
        self.obj1.orte.add(o)
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(self.model_admin.orte_string(obj), 'Dortmund, XYZ')


class TestAutorAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.AutorAdmin
    model = _models.Autor
    exclude_expected = ['magazin']
    fields_expected = ['kuerzel', 'beschreibung', 'bemerkungen', 'person']
    search_fields_expected = ['_name', 'beschreibung', 'bemerkungen']
    raw_data = [
        {'magazin__magazin_name': ['Testmagazin1', 'Testmagazin2']}
    ]
    crosslinks_object_data = {'artikel__extra': 1, 'magazin__extra': 1, 'buch__extra': 1}
    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'autor', 'label': 'Artikel (1)'},
        {'model_name': 'buch', 'fld_name': 'autor', 'label': 'Bücher (1)'},
    ]

    def test_magazin_string(self):
        obj = self.obj1.qs().annotate(**self.model_admin.get_result_list_annotations()).get()
        self.assertEqual(
            self.model_admin.magazin_string(obj),
            'Testmagazin1, Testmagazin2'
        )


class TestOrtAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.OrtAdmin
    model = _models.Ort
    fields_expected = ['stadt', 'land', 'bland']
    search_fields_expected = ['_name']
    test_data_count = 1

    crosslinks_expected = [
        {'model_name': 'artikel', 'fld_name': 'ort', 'label': 'Artikel (1)'},
        {'model_name': 'audio', 'fld_name': 'ort', 'label': 'Audio Materialien (1)'},
        {'model_name': 'band', 'fld_name': 'orte', 'label': 'Bands (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'ort', 'label': 'Bild Materialien (1)'},
        {'model_name': 'buch', 'fld_name': 'ort', 'label': 'Bücher (1)'},
        {'model_name': 'datei', 'fld_name': 'ort', 'label': 'Dateien (1)'},
        {'model_name': 'dokument', 'fld_name': 'ort', 'label': 'Dokumente (1)'},
        {'model_name': 'magazin', 'fld_name': 'orte', 'label': 'Magazine (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'ort', 'label': 'Memorabilien (1)'},
        {'model_name': 'musiker', 'fld_name': 'orte', 'label': 'Musiker (1)'},
        {'model_name': 'person', 'fld_name': 'orte', 'label': 'Personen (1)'},
        {'model_name': 'spielort', 'fld_name': 'ort', 'label': 'Spielorte (1)'},
        {'model_name': 'technik', 'fld_name': 'ort', 'label': 'Technik (1)'},
        {'model_name': 'verlag', 'fld_name': 'sitz', 'label': 'Verlage (1)'},
        {'model_name': 'video', 'fld_name': 'ort', 'label': 'Video Materialien (1)'}
    ]

    def bland_forwarded(self):
        f = self.model_admin.get_form(self.get_request())
        self.assertEqual(f.base_fields['bland'].widget.widget.forward[0], ['land'])


class TestLandAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.LandAdmin
    model = _models.Land
    fields_expected = ['land_name', 'code']
    search_fields_expected = ['land_name', 'code', 'pk__iexact']
    test_data_count = 1
    add_page_uses_select2 = False
    changelist_uses_select2 = False

    crosslinks_expected = [
        {'model_name': 'ort', 'fld_name': 'land', 'label': 'Orte (1)'},
        {'model_name': 'bundesland', 'fld_name': 'land', 'label': 'Bundesländer (1)'}
    ]


class TestBlandAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.BlandAdmin
    model = _models.Bundesland
    fields_expected = ['bland_name', 'code', 'land']
    search_fields_expected = ['bland_name', 'code']
    test_data_count = 1

    crosslinks_expected = [
        {'model_name': 'ort', 'fld_name': 'bland', 'label': 'Orte (1)'}
    ]


class TestInstrumentAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.InstrumentAdmin
    model = _models.Instrument
    fields_expected = ['instrument', 'kuerzel']
    search_fields_expected = ['instrument', 'kuerzel', 'pk__iexact']
    test_data_count = 1
    add_page_uses_select2 = False
    changelist_uses_select2 = False

    crosslinks_expected = [
        {'model_name': 'musiker', 'fld_name': 'instrument', 'label': 'Musiker (1)'}
    ]


class TestAudioAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.AudioAdmin
    model = _models.Audio
    exclude_expected = [
        'plattenfirma', 'band', 'genre', 'musiker', 'person', 'schlagwort',
        'spielort', 'veranstaltung', 'ort'
    ]
    fields_expected = [
        'titel', 'tracks', 'laufzeit', 'jahr', 'quelle', 'original',
        'plattennummer', 'release_id', 'discogs_url', 'beschreibung',
        'bemerkungen', 'medium', 'medium_qty'
    ]
    search_fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    raw_data = [
        {
            'band__band_name': 'Testband',
            'musiker__kuenstler_name': 'Alice Tester'
        }
    ]

    def test_kuenstler_string(self):
        self.assertEqual(
            self.model_admin.kuenstler_string(self.obj1),
            'Testband, Alice Tester'
        )


class TestSpielortAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.SpielortAdmin
    model = _models.Spielort
    fields_expected = ['name', 'beschreibung', 'bemerkungen', 'ort']
    search_fields_expected = [
        'name', 'spielortalias__alias', 'beschreibung', 'bemerkungen']
    test_data_count = 1
    changelist_uses_select2 = False

    crosslinks_expected = [
        {'model_name': 'dokument', 'fld_name': 'spielort', 'label': 'Dokumente (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'spielort', 'label': 'Memorabilien (1)'},
        {'model_name': 'video', 'fld_name': 'spielort', 'label': 'Video Materialien (1)'},
        {'model_name': 'kalender', 'fld_name': 'spielort', 'label': 'Programmhefte (1)'},
        {'model_name': 'buch', 'fld_name': 'spielort', 'label': 'Bücher (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'spielort', 'label': 'Bild Materialien (1)'},
        {'model_name': 'datei', 'fld_name': 'spielort', 'label': 'Dateien (1)'},
        {'model_name': 'artikel', 'fld_name': 'spielort', 'label': 'Artikel (1)'},
        {'model_name': 'audio', 'fld_name': 'spielort', 'label': 'Audio Materialien (1)'},
        {'model_name': 'technik', 'fld_name': 'spielort', 'label': 'Technik (1)'},
        {'model_name': 'veranstaltung', 'fld_name': 'spielort', 'label': 'Veranstaltungen (1)'}
    ]


class TestVeranstaltungAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.VeranstaltungAdmin
    model = _models.Veranstaltung
    exclude_expected = ['genre', 'person', 'band', 'schlagwort', 'musiker']
    fields_expected = ['name', 'datum', 'spielort', 'reihe', 'beschreibung', 'bemerkungen']
    search_fields_expected = [
        'name', 'datum', 'veranstaltungalias__alias', 'beschreibung', 'bemerkungen']
    test_data_count = 1
    changelist_uses_select2 = False

    crosslinks_expected = [
        {'model_name': 'technik', 'fld_name': 'veranstaltung', 'label': 'Technik (1)'},
        {'model_name': 'dokument', 'fld_name': 'veranstaltung', 'label': 'Dokumente (1)'},
        {'model_name': 'memorabilien', 'fld_name': 'veranstaltung', 'label': 'Memorabilien (1)'},
        {'model_name': 'video', 'fld_name': 'veranstaltung', 'label': 'Video Materialien (1)'},
        {'model_name': 'kalender', 'fld_name': 'veranstaltung', 'label': 'Programmhefte (1)'},
        {'model_name': 'buch', 'fld_name': 'veranstaltung', 'label': 'Bücher (1)'},
        {'model_name': 'bildmaterial', 'fld_name': 'veranstaltung', 'label': 'Bild Materialien (1)'},
        {'model_name': 'datei', 'fld_name': 'veranstaltung', 'label': 'Dateien (1)'},
        {'model_name': 'artikel', 'fld_name': 'veranstaltung', 'label': 'Artikel (1)'},
        {'model_name': 'audio', 'fld_name': 'veranstaltung', 'label': 'Audio Materialien (1)'}
    ]


class TestVerlagAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.VerlagAdmin
    model = _models.Verlag
    fields_expected = ['verlag_name', 'sitz']
    search_fields_expected = ['verlag_name']
    crosslinks_expected = [
        {'model_name': 'buch', 'fld_name': 'verlag', 'label': 'Bücher (1)'},
        {'model_name': 'magazin', 'fld_name': 'verlag', 'label': 'Magazine (1)'}
    ]


class TestBuchAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BuchAdmin
    model = _models.Buch
    exclude_expected = [
        'herausgeber', 'verlag', 'autor', 'genre', 'schlagwort', 'person', 'band',
        'musiker', 'ort', 'spielort', 'veranstaltung'
    ]
    fields_expected = [
        'titel', 'titel_orig', 'seitenumfang', 'jahr', 'jahr_orig', 'auflage',
        'EAN', 'ISBN', 'is_buchband', 'beschreibung', 'bemerkungen',
        'schriftenreihe', 'buchband', 'sprache',
    ]
    search_fields_expected = ['titel', 'beschreibung', 'bemerkungen']

    crosslinks_expected = [
        {'model_name': 'buch', 'fld_name': 'buchband', 'label': 'Aufsätze (1)'},
    ]

    @classmethod
    def setUpTestData(cls):
        p1 = make(_models.Person, vorname='Alice', nachname='Testman')
        p2 = make(_models.Person, vorname='Bob', nachname='Mantest')
        cls.obj1 = make(
            cls.model,
            autor__person=[p1, p2], herausgeber__herausgeber=[str(p1), str(p2)],
            schlagwort__schlagwort=['Testschlagwort1', 'Testschlagwort2'],
            genre__genre=['Testgenre1', 'Testgenre2']
        )
        cls.test_data = [cls.obj1]
        super().setUpTestData()

    def test_autoren_string(self):
        self.assertEqual(
            self.model_admin.autoren_string(self.obj1),
            'Alice Testman (AT), Bob Mantest (BM)'
        )

    def test_herausgeber_string(self):
        self.assertEqual(
            self.model_admin.herausgeber_string(self.obj1),
            'Alice Testman, Bob Mantest'
        )

    def test_schlagwort_string(self):
        self.assertEqual(
            self.model_admin.schlagwort_string(self.obj1),
            'Testschlagwort1, Testschlagwort2'
        )

    def test_genre_string(self):
        self.assertEqual(
            self.model_admin.genre_string(self.obj1),
            'Testgenre1, Testgenre2'
        )


class TestBaseBrochureAdmin(AdminTestCase):
    model_admin_class = _admin.BaseBrochureAdmin
    model = _models.Brochure

    @translation_override(language=None)
    def test_get_fieldsets(self):
        # Assert that an extra fieldset vor the (ausgabe__magazin, ausgabe)
        # group was added.
        fieldsets = self.model_admin.get_fieldsets(self.get_request())
        # Should have three fieldsets:
        # the default 'none',
        # beschreibung & bemerkungen
        # and the ausgabe & ausgabe__magazin one.
        self.assertEqual(len(fieldsets), 3)
        self.assertEqual(fieldsets[1][0], 'Beilage von Ausgabe')
        fieldset_options = fieldsets[1][1]
        self.assertIn('fields', fieldset_options)
        self.assertEqual(
            fieldset_options['fields'], [('ausgabe__magazin', 'ausgabe')])
        self.assertIn('description', fieldset_options)
        self.assertEqual(
            fieldset_options['description'],
            'Geben Sie die Ausgabe an, der dieses Objekt beilag.'
        )


class TestBrochureAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BrochureAdmin
    model = _models.Brochure
    fields_expected = [
        'titel', 'zusammenfassung', 'bemerkungen', 'ausgabe', 'beschreibung',
        'ausgabe__magazin'
    ]
    exclude_expected = ['genre', 'schlagwort']
    search_fields_expected = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']


class TestKatalogAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.KatalogAdmin
    model = _models.Katalog
    fields_expected = [
        'titel', 'zusammenfassung', 'bemerkungen', 'ausgabe', 'beschreibung',
        'art', 'ausgabe__magazin'
    ]
    exclude_expected = ['genre']
    search_fields_expected = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']

    def test_get_fieldsets(self):
        # Assert that 'art' and 'zusammenfassung' are swapped correctly
        none_fieldset_options = self.model_admin.get_fieldsets(self.get_request())[0][1]
        self.assertIn('fields', none_fieldset_options)
        self.assertIn('art', none_fieldset_options['fields'])
        art_index = none_fieldset_options['fields'].index('art')
        self.assertIn('zusammenfassung', none_fieldset_options['fields'])
        z_index = none_fieldset_options['fields'].index('zusammenfassung')
        self.assertTrue(art_index < z_index)


class TestKalenderAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.KalenderAdmin
    model = _models.Kalender
    fields_expected = [
        'titel', 'zusammenfassung', 'bemerkungen', 'ausgabe', 'beschreibung',
        'ausgabe__magazin'
    ]
    exclude_expected = ['genre', 'spielort', 'veranstaltung']
    search_fields_expected = ['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen']


@skip("Unfinished model/ModelAdmin")
class TestMemoAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.MemoAdmin
    model = _models.Memorabilien
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort',
        'veranstaltung'
    ]
    search_fields_expected = ['titel', 'beschreibung', 'bemerkungen', 'pk__iexact']


@skip("Unfinished model/ModelAdmin")
class TestDokumentAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.DokumentAdmin
    model = _models.Dokument
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort',
        'veranstaltung'
    ]
    search_fields_expected = ['titel', 'beschreibung', 'bemerkungen', 'pk__iexact']


@skip("Unfinished model/ModelAdmin")
class TestTechnikAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.TechnikAdmin
    model = _models.Technik
    fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort',
        'veranstaltung'
    ]
    search_fields_expected = ['titel', 'beschreibung', 'bemerkungen', 'pk__iexact']


class TestVideoAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.VideoAdmin
    model = _models.Video
    fields_expected = [
        'titel', 'laufzeit', 'jahr', 'quelle', 'original', 'release_id', 'discogs_url',
        'beschreibung', 'bemerkungen', 'medium', 'medium_qty'
    ]
    search_fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = [
        'band', 'genre', 'musiker', 'person', 'schlagwort', 'ort', 'spielort', 'veranstaltung']


class TestBestandAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.BestandAdmin
    model = _models.Bestand
    fields_expected = [
        'lagerort', 'provenienz', 'audio', 'ausgabe', 'bildmaterial',
        'brochure', 'buch', 'dokument', 'memorabilien', 'technik', 'video'
    ]

    def test_bestand_class(self):
        # Assert that list_display method bestand_class returns the verbose_name
        # of the model that is referenced by the particular Bestand instance.
        obj = make(self.model)
        self.assertFalse(self.model_admin.bestand_class(obj))
        obj = make(self.model, audio=make(_models.Audio))
        self.assertEqual(self.model_admin.bestand_class(obj), _models.Audio._meta.verbose_name)

    def test_bestand_link(self):
        # Assert that list_display method bestand_link returns a hyperlink to
        # the instance that is referenced by the particular Bestand instance.
        obj = make(self.model)
        self.assertFalse(self.model_admin.bestand_link(obj))
        obj = make(self.model, audio=make(_models.Audio))
        # Need to set a request attribute on the model_admin instance:
        self.model_admin.request = self.get_request()
        link = self.model_admin.bestand_link(obj)
        self.assertTrue(link.startswith('<a'))
        self.assertIn('target="_blank"', link)
        self.assertIn(str(obj.audio.pk), link)


class TestDateiAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.DateiAdmin
    model = _models.Datei
    fields_expected = [
        'titel', 'media_typ', 'datei_pfad', 'beschreibung', 'bemerkungen', 'provenienz']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band', 'musiker', 'ort', 'spielort',
        'veranstaltung'
    ]
    search_fields_expected = ['titel', 'beschreibung', 'bemerkungen', 'pk__iexact']
    changelist_uses_select2 = False


class TestHerausgeberAdmin(AdminTestMethodsMixin, AdminTestCase):
    model_admin_class = _admin.HerausgeberAdmin
    model = _models.Herausgeber
    fields_expected = ['herausgeber']
    search_fields_expected = ['herausgeber', 'pk__iexact']
    add_page_uses_select2 = False
    changelist_uses_select2 = False

    crosslinks_expected = [
        {'model_name': 'buch', 'fld_name': 'herausgeber', 'label': 'Bücher (1)'},
        {'model_name': 'magazin', 'fld_name': 'herausgeber', 'label': 'Magazine (1)'}
    ]


class TestBildmaterialAdmin(AdminTestMethodsMixin, AdminTestCase):

    model_admin_class = _admin.BildmaterialAdmin
    model = _models.Bildmaterial
    test_data_count = 1

    fields_expected = [
        'titel', 'signatur', 'size', 'datum', 'beschreibung',
        'bemerkungen', 'reihe', 'copy_related'
    ]
    search_fields_expected = ['titel', 'beschreibung', 'bemerkungen']
    exclude_expected = [
        'genre', 'schlagwort', 'person', 'band',
        'musiker', 'ort', 'spielort', 'veranstaltung'
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.band = make(_models.Band)
        cls.musiker = make(_models.Musiker)
        cls.veranstaltung = make(
            _models.Veranstaltung, band=[cls.band], musiker=[cls.musiker])
        cls.obj1.veranstaltung.add(cls.veranstaltung)

    def test_copy_related_set(self):
        self.model_admin.copy_related(self.obj1)
        self.assertIn(self.band, self.obj1.band.all())
        self.assertIn(self.musiker, self.obj1.musiker.all())

    def test_reponse_add(self):
        request = self.post_request(data={'copy_related': True})
        self.model_admin.response_add(request, self.obj1)
        self.assertIn(self.band, self.obj1.band.all())
        self.assertIn(self.musiker, self.obj1.musiker.all())

    def test_reponse_add_no_copy(self):
        request = self.post_request(data={})
        self.model_admin.response_add(request, self.obj1)
        self.assertNotIn(self.band, self.obj1.band.all())
        self.assertNotIn(self.musiker, self.obj1.musiker.all())

    def test_reponse_change(self):
        request = self.post_request(data={'copy_related': True})
        self.model_admin.response_change(request, self.obj1)
        self.assertIn(self.band, self.obj1.band.all())
        self.assertIn(self.musiker, self.obj1.musiker.all())

    def test_reponse_change_no_copy(self):
        request = self.post_request(data={})
        self.model_admin.response_change(request, self.obj1)
        self.assertNotIn(self.band, self.obj1.band.all())
        self.assertNotIn(self.musiker, self.obj1.musiker.all())


class TestAuthAdminMixin(TestCase):

    @patch('DBentry.admin.super')
    def test_formfield_for_manytomany(self, mocked_super):
        # Assert that formfield_for_manytomany adds a (<model_class_name>) to
        # the human-readable part of the formfield's choices.
        ct = contenttypes.models.ContentType.objects.get_for_model(_models.AusgabeLnum)
        perm_queryset = Permission.objects.filter(content_type=ct)
        mocked_formfield = Mock(queryset=perm_queryset)
        mocked_super.return_value = Mock(
            formfield_for_manytomany=Mock(return_value=mocked_formfield))
        formfield = _admin.AuthAdminMixin().formfield_for_manytomany(None)
        for choice in formfield.choices:
            with self.subTest(choice=choice):
                self.assertIn(_models.AusgabeLnum.__name__, choice[1])


class TestMIZChangelist(AdminTestCase):

    model = _models.Genre
    model_admin_class = _admin.GenreAdmin

    @patch.object(_admin.GenreAdmin, 'get_result_list_annotations')
    def test_adds_annotations(self, mocked_get_annotations):
        # Assert that list_display annotations are added.
        request = self.get_request(path=self.changelist_path)
        changelist = self.model_admin.get_changelist_instance(request)
        mocked_get_annotations.return_value = {}
        changelist.get_results(request)
        self.assertFalse(changelist.result_list.query.annotations)
        from django.db.models import Count
        mocked_get_annotations.return_value = {'c': Count('artikel')}
        changelist.get_results(request)
        self.assertIn('c', changelist.result_list.query.annotations)
