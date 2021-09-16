import re
from unittest.mock import patch, Mock
from collections import OrderedDict

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.urls import reverse, resolve
from django.utils.http import unquote

from dbentry import models as _models
from dbentry import utils
from dbentry.actions.views import MergeViewWizarded
from dbentry.factory import make
from dbentry.maint.views import (
    DuplicateObjectsView, ModelSelectView, UnusedObjectsView, find_duplicates
)
from dbentry.tests.base import ViewTestCase, DataTestCase
from dbentry.tests.mixins import TestDataMixin


class TestModelSelectView(ViewTestCase):

    view_class = ModelSelectView

    def test_get_context_data(self):
        initkwargs = {
            'submit_value': 'testing_value',
            'submit_name': 'testing_name',
            'form_method': 'testing_form_method'
        }
        view = self.get_view(self.get_request(), **initkwargs)
        context = view.get_context_data()
        for context_variable, expected in initkwargs.items():
            with self.subTest(var=context_variable):
                self.assertIn(context_variable, context)
                self.assertEqual(context[context_variable], expected)

    def test_get(self):
        # Assert that get() redirects to the success url if
        # the view's submit_name is in the GET querydict.
        request = self.get_request(data={'testing': 'yes'})
        view = self.get_view(request, submit_name='testing')
        with patch.object(view, 'get_success_url', return_value='admin:index'):
            response = view.get(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/')

    def test_get_success_url(self):
        # Assert that get_success_url returns a resolvable url.
        view = self.get_view(self.get_request(), next_view='admin:index')
        with patch.object(view, 'get_next_view_kwargs', return_value={}):
            self.assertEqual(view.get_success_url(), '/admin/')

    def test_get_next_view_kwargs(self):
        view = self.get_view(self.get_request(data={'model_select': 'some_model'}))
        self.assertEqual(view.get_next_view_kwargs(), {'model_name': 'some_model'})


class TestDuplicateObjectsView(TestDataMixin, ViewTestCase):

    model = _models.Band
    view_class = DuplicateObjectsView

    @classmethod
    def setUpTestData(cls):
        cls.genre1 = make(_models.Genre)
        cls.genre2 = make(_models.Genre)
        cls.test_data = []
        for i in range(1, 4):
            # Note that we are not using make() here, as the factory for the
            # Band model uses get_or_create with the field 'band_name'.
            # make(Band, band_name='Beep') will try to get() an existing Band
            # instance with band_name = 'Beep' before creating a new one.
            obj = _models.Band.objects.create(id=i, band_name='Beep')
            obj.genre.set([cls.genre1, cls.genre2])
            cls.test_data.append(obj)
        super().setUpTestData()

    def test_availability(self):
        url = reverse('dupes', kwargs={'model_name': 'band'})
        self.assertTrue(resolve(url))

        # Assert that no queries are being done accessing the page; an oversight
        # led to the page querying for duplicates without any fields when request.
        # one query each for: session, user (must be a client thing)
        with self.assertNumQueries(2):
            self.client.get(url)

    def test_setup_exception(self):
        # Assert that setup() raises a TypeError when 'model_name' kwarg is
        # missing.
        view = self.view_class()
        request = self.get_request()
        with self.assertRaises(TypeError):
            view.setup(request)

    def test_post_redirects_to_self_after_merging(self):
        # Assert that post redirects back to itself after a merge.
        path = reverse('dupes', kwargs={'model_name': 'band'})
        request = self.post_request(path, data={ACTION_CHECKBOX_NAME: ['1', '2']})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        # Patch the as_view method of MergeViewWizarded to return None,
        # thereby emulating a successful merge without conflicts.
        mocked_as_view = Mock(return_value=Mock(return_value=None))
        with patch.object(MergeViewWizarded, 'as_view', new=mocked_as_view):
            response = view.post(request)
            self.assertEqual(response.url, path)

    # noinspection PyUnresolvedReferences
    def test_post_calls_merge_view(self):
        # Assert that a post request will call the merge view.
        model_admin = utils.get_model_admin_for_model(self.model)
        request = self.post_request(data={ACTION_CHECKBOX_NAME: ['1', '2']})
        view = self.get_view(request, kwargs={'model_name': 'band'})

        with patch.object(MergeViewWizarded, 'as_view') as mocked_as_view:
            view.post(request)
        self.assertEqual(mocked_as_view.call_count, 1)
        kwargs = mocked_as_view.call_args[1]
        self.assertIn('model_admin', kwargs)
        self.assertEqual(kwargs['model_admin'].__class__, model_admin.__class__)
        self.assertIn('queryset', kwargs)
        self.assertEqual(
            list(kwargs['queryset'].values_list('pk', flat=True)),
            [self.obj1.pk, self.obj2.pk]
        )

    def test_post_does_not_call_merge_view_with_no_selects(self):
        # Assert that a post request will NOT call the merge view when no items
        # in a sub list are selected for a merge.
        request = self.post_request(data={ACTION_CHECKBOX_NAME: []})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        with patch.object(MergeViewWizarded, 'as_view') as mocked_as_view:
            view.post(request)
        self.assertEqual(mocked_as_view.call_count, 0)

    def test_build_duplicates_items(self):
        # Assert that build_duplicates_items returns the correct items.
        changeform_url = unquote(
            reverse('admin:dbentry_band_change', args=['{pk}'])
        )
        link_template = '<a href="{url}" target="_blank">{name}</a>'

        request = self.get_request(
            data={
                'base': ['band_name', 'beschreibung'], 'm2m': ['genre'],
                'base_display': ['band_name', 'beschreibung'],
                'm2m_display': ['genre']
            }
        )
        view = self.get_view(request, kwargs={'model_name': 'band'})
        form = view.get_form()
        # A validated and cleaned form is required.
        self.assertTrue(form.is_valid())

        items = view.build_duplicates_items(form)
        self.assertEqual(
            len(items), 1,
            msg="There should be only one set of duplicate objects. %r" % items
        )
        self.assertEqual(
            len(items[0]), 2,
            msg="Should contain one set of duplicate objects and the link to "
            "their changelist."
        )
        self.assertEqual(
            len(items[0][0]), 3,
            msg="Should contain the three duplicate objects."
        )
        for dupe_item in items[0][0]:
            with self.subTest():
                self.assertEqual(
                    len(dupe_item), 3,
                    msg="Each dupe item is expected to have 3 attributes."
                )
                self.assertIsInstance(
                    dupe_item[0], self.model,
                    msg="Duplicate object should be an instance of "
                    "{!s}.".format(self.model)
                )
                expected_link = link_template.format(
                    url=changeform_url.format(pk=dupe_item[0].pk),
                    name=str(dupe_item[0])
                )
                self.assertEqual(
                    dupe_item[1], expected_link,
                    msg="Should be link to change form of object."
                )
                self.assertEqual(
                    len(dupe_item[2]), 3,
                    msg=(
                        "Expected each dupe item to have three values: band_name,"
                        " beschreibung, genres"
                    )
                )
                # band_name:
                self.assertEqual(
                    dupe_item[2][0], 'Beep', msg="Band names do not match.")
                # beschreibung:
                self.assertEqual(
                    dupe_item[2][1], '', msg="Beschreibung does not match.")
                # genres:
                genre_pks = ", ".join(
                    pk for pk in sorted([str(self.genre1.pk), str(self.genre2.pk)]))
                self.assertEqual(
                    # Enforce an alphabetical order.
                    ", ".join(v for v in sorted(dupe_item[2][2].split(", "))),
                    genre_pks,
                    msg="Genres do not match."
                )
        # Investigate the link to the changelist:
        cl_link = items[0][1]
        self.assertIsInstance(cl_link, str)
        match = re.match(r'<a (.*)>(\w+)</a>', cl_link)
        self.assertTrue(
            match, msg="Should be the link to the changelist of the duplicate objects.")
        attrs, content = match.groups()
        self.assertEqual(content, 'Änderungsliste')
        attrs = dict(attr.replace('"', '').split("=", 1) for attr in attrs.split(" "))
        self.assertIn("href", attrs)
        self.assertEqual(
            attrs['href'].count('?'), 1,
            msg="Changelist url should be of format <changelist>?id__in=[ids]")
        cl_url, query_params = attrs['href'].split('?')
        self.assertEqual(reverse('admin:dbentry_band_changelist'), cl_url)
        self.assertEqual("id__in=" + ",".join(str(o.pk) for o in self.test_data), query_params)
        self.assertIn("target", attrs)
        self.assertEqual(attrs['target'], '_blank')
        self.assertIn("class", attrs)
        self.assertEqual(attrs["class"], "button")

    def test_build_duplicates_headers(self):
        # Assert that the correct (field.verbose_name capitalized) headers are
        # returned. Headers are built from the labels of the established choices.
        test_data = [
            ({'base': ['band_name'], 'base_display': ['band_name']}, 'Bandname'),
            ({'m2m': ['genre'], 'm2m_display': ['genre']}, 'Genre'),
            ({'reverse': ['bandalias__alias'], 'reverse_display': ['bandalias__alias']}, 'Alias')
        ]
        for request_data, expected in test_data:
            with self.subTest(data=request_data):
                request = self.get_request(data=request_data)
                view = self.get_view(request, kwargs={'model_name': 'band'})
                form = view.get_form()
                self.assertTrue(form.is_valid())
                headers = view.build_duplicates_headers(form)
                self.assertIn(expected, headers)

    def test_build_duplicates_headers_grouped_choices(self):
        request = self.get_request(
            data={
                'reverse': ['bandalias__alias'],
                'reverse_display': ['bandalias__alias']
            }
        )
        view = self.get_view(request, kwargs={'model_name': 'band'})
        form = view.get_form()
        form.fields['reverse'].choices = [
            ('Alias', [('bandalias__alias', 'Alias')])
        ]
        self.assertTrue(form.is_valid())
        headers = view.build_duplicates_headers(form)
        self.assertIn('Alias', headers)


class TestUnusedObjectsView(ViewTestCase):

    view_class = UnusedObjectsView

    @classmethod
    def setUpTestData(cls):
        cls.artikel1 = make(_models.Artikel)
        cls.artikel2 = make(_models.Artikel)

        cls.unused = make(_models.Genre)
        cls.used_once = make(_models.Genre)
        cls.artikel1.genre.add(cls.used_once)
        cls.used_twice = make(_models.Genre)
        cls.artikel1.genre.add(cls.used_twice)
        cls.artikel2.genre.add(cls.used_twice)
        cls.test_data = [cls.unused, cls.used_once, cls.used_twice]
        super().setUpTestData()

    def test_get_queryset(self):
        # Assert that the returned querysets return the correct amount of
        # 'unused' records.
        view = self.get_view(request=self.get_request())
        for limit in [0, 1, 2]:
            relations, queryset = view.get_queryset(_models.Genre, limit)
            with self.subTest(limit=limit):
                self.assertEqual(queryset.count(), limit + 1)

    @patch.object(UnusedObjectsView, 'build_items')
    @patch.object(UnusedObjectsView, 'render_to_response')
    def test_get_form_invalid(self, mocked_render, _mocked_build_items):
        # Assert that the get response with an invalid form does not contain
        # the context variable 'items'.
        data = {'get_unused': True, 'model_select': 'NotAModel', 'limit': 0}
        request = self.get_request(data=data)
        view = self.get_view(request=request)
        self.assertFalse(view.get_form().is_valid())
        view.get(request=request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertNotIn('items', context.keys())

    @patch.object(UnusedObjectsView, 'build_items')
    @patch.object(UnusedObjectsView, 'render_to_response')
    def test_get_form_valid(self, mocked_render, _mocked_build_items):
        # Assert that the get response with a valid form contains the
        # context variable 'items'.
        data = {'get_unused': True, 'model_select': 'artikel', 'limit': 0}
        request = self.get_request(data=data)
        view = self.get_view(request=request)
        self.assertTrue(view.get_form().is_valid())
        view.get(request=request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertIn('items', context.keys())

    def test_build_items(self):
        # Check the contents of the list that build_items returns.
        relations = OrderedDict()
        relations['artikel_rel'] = {
            'related_model': _models.Artikel,
            'counts': {self.unused.pk: '0', self.used_once.pk: '1'}
        }
        queryset = _models.Genre.objects.filter(pk__in=[self.unused.pk, self.used_once.pk])

        items = self.get_view(self.get_request()).build_items(relations, queryset)
        self.assertEqual(len(items), 2)
        # Sorting by "model_name (count)" since we know count is either 0 or 1:
        # (sorting by url will sort an url with pk="10" before one with pk="9")
        unused, used_once = sorted(items, key=lambda tpl: tpl[1])
        url = reverse("admin:dbentry_genre_change", args=[self.unused.pk])
        self.assertIn(url, unused[0])
        self.assertIn("Artikel (0)", unused[1])
        url = reverse("admin:dbentry_genre_change", args=[self.used_once.pk])
        self.assertIn(url, used_once[0])
        self.assertIn("Artikel (1)", used_once[1])

    @patch.object(UnusedObjectsView, 'build_items')
    @patch.object(UnusedObjectsView, 'render_to_response')
    def test_get_changelist_link(self, mocked_render, _mocked_build_items):
        # Assert that the response's context contains a link to the changelist
        # listing all the unused objects.
        data = {'get_unused': True, 'model_select': 'genre', 'limit': 0}
        request = self.get_request(data=data)
        view = self.get_view(request=request)
        self.assertTrue(view.get_form().is_valid())
        view.get(request=request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertIn('changelist_link', context.keys())
        link = context['changelist_link']
        cl_url = reverse('admin:dbentry_genre_changelist') + "?id__in=" + str(self.unused.pk)
        # Too lazy to unpack the html element with regex to check its other attributes.
        self.assertIn(cl_url, link)


class TestDuplicates(DataTestCase):

    model = _models.Musiker

    @classmethod
    def setUpTestData(cls):
        cls.test_data = [
            cls.model.objects.create(kuenstler_name='Bob'),
            cls.model.objects.create(kuenstler_name='Bob'),
            cls.model.objects.create(kuenstler_name='Bob'),
        ]

        super().setUpTestData()

    def get_duplicate_instances(self, dupe_fields, display_fields=None, queryset=None):
        # Query for the duplicates and return the duplicate model instances.
        if queryset is None:
            queryset = self.queryset
        duplicates = find_duplicates(queryset, dupe_fields, display_fields or ())
        instances = []
        for dupe_group in duplicates:
            for dupe in dupe_group:
                instances.append(dupe.instance)
        return instances

    # noinspection PyUnresolvedReferences
    def test_find_duplicates(self):
        # Assert that the three duplicates instances are found.
        duplicates = self.get_duplicate_instances(['kuenstler_name'])
        msg = "Expected to find %r among the duplicate instances."
        self.assertIn(self.obj1, duplicates, msg=msg % self.obj1)
        self.assertIn(self.obj2, duplicates, msg=msg % self.obj2)
        self.assertIn(self.obj3, duplicates, msg=msg % self.obj3)

    def test_empty(self):
        # Assert that duplicates are not found by comparing empty values.
        duplicates = self.get_duplicate_instances(['beschreibung'])
        msg = "Unexpectedly found %r as duplicate by querying an empty field."
        for obj in self.test_data:
            with self.subTest(obj=obj):
                self.assertNotIn(obj, duplicates, msg=msg % obj)

    # noinspection PyUnresolvedReferences
    def test_duplicates_m2m(self):
        # Assert that duplicates can be found by comparing m2m fields.
        g1 = make(_models.Genre)
        g2 = make(_models.Genre)

        # Add identical genres to obj1 and obj2.
        self.obj1.genre.add(g1)
        self.obj2.genre.add(g1)
        duplicates = self.get_duplicate_instances(['kuenstler_name', 'genre'])
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        # Comparing on the m2m field 'genre' should have failed for obj3:
        self.assertNotIn(self.obj3, duplicates)

        # Add a different genre to obj3.
        # The results should be the same as above.
        self.obj3.genre.add(g2)
        duplicates = self.get_duplicate_instances(['kuenstler_name', 'genre'])
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

        # obj1 and obj2 share a genre, but their total genres are not the same.
        self.obj1.genre.add(g2)
        duplicates = self.get_duplicate_instances(['kuenstler_name', 'genre'])
        self.assertNotIn(self.obj1, duplicates)
        self.assertNotIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

    # noinspection PyUnresolvedReferences
    def test_duplicates_reverse_fk(self):
        # Assert that duplicates can be found by comparing reverse FK fields.
        # Add the same alias to both obj1 and obj2:
        self.obj1.musikeralias_set.create(alias='Beep')
        self.obj2.musikeralias_set.create(alias='Beep')
        duplicates = self.get_duplicate_instances(['kuenstler_name', 'musikeralias__alias'])
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        # obj3 does not share the aliases of obj1 or obj2:
        self.assertNotIn(self.obj3, duplicates)

        # Add a different alias to obj3.
        # The results should be the same as above:
        self.obj3.musikeralias_set.create(alias='Boop')
        duplicates = self.get_duplicate_instances(['kuenstler_name', 'musikeralias__alias'])
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

        # Add another alias to obj1.
        # None of the Musiker instances should be duplicates now:
        self.obj1.musikeralias_set.create(alias='Boop')
        duplicates = self.get_duplicate_instances(['kuenstler_name', 'musikeralias__alias'])
        self.assertNotIn(self.obj1, duplicates)
        self.assertNotIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

    # noinspection PyUnresolvedReferences
    def test_duplicates_reverse_fk_joins(self):
        # Assert that the number of duplicates found is not affected by table joins.
        self.obj1.musikeralias_set.create(alias='Beep')
        self.obj2.musikeralias_set.create(alias='Beep')
        self.obj1.musikeralias_set.create(alias='Boop')
        self.obj2.musikeralias_set.create(alias='Boop')
        duplicates = self.get_duplicate_instances(['kuenstler_name', 'musikeralias__alias'])
        self.assertEqual(len(duplicates), 2)

    def test_duplicate_values(self):
        # Check the 'duplicate_values' returned by find_duplicates.
        self.queryset.update(beschreibung='Rival Sons are pretty good.')
        duplicates = find_duplicates(
            self.queryset, dupe_fields=['kuenstler_name', 'beschreibung'], display_fields=())
        self.assertEqual(len(duplicates), 1, msg="Expected only one dupe group.")
        self.assertEqual(len(duplicates[0]), 3, msg="Expected three dupes.")
        for dupe in duplicates[0]:
            with self.subTest(dupe=dupe):
                self.assertIn(
                    'kuenstler_name', dupe.duplicate_values,
                    msg="Expected field 'kuenstler_name' to be in dupe_values."
                )
                self.assertEqual(dupe.duplicate_values['kuenstler_name'], ('Bob', ))

                self.assertIn(
                    'beschreibung', dupe.duplicate_values,
                    msg="Expected field 'beschreibung' to be in dupe_values."
                )
                self.assertEqual(
                    dupe.duplicate_values['beschreibung'], ('Rival Sons are pretty good.', ))

    def test_display_values(self):
        # Check the 'display values' returned by find_duplicates.
        self.queryset.update(beschreibung='Rival Sons are pretty good.')
        duplicates = find_duplicates(
            self.queryset, dupe_fields=['kuenstler_name'], display_fields=['beschreibung'])
        self.assertEqual(len(duplicates), 1, msg="Expected only one dupe group.")
        self.assertEqual(len(duplicates[0]), 3, msg="Expected three dupes.")
        for dupe in duplicates[0]:
            with self.subTest(dupe=dupe):
                self.assertIn(
                    'beschreibung', dupe.display_values,
                    msg="Expected field 'beschreibung' to be in display_values."
                )
                self.assertEqual(
                    dupe.display_values['beschreibung'], ('Rival Sons are pretty good.', ))
