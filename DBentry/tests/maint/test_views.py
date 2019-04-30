from ..base import ViewTestCase
from ..mixins import TestDataMixin

from unittest.mock import patch, Mock

from django.urls import reverse
from django.utils.http import unquote
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME

from DBentry.maint.views import DuplicateObjectsView
from DBentry.actions.views import MergeViewWizarded

from DBentry import models as _models
from DBentry import utils

class TestDuplicateObjectsView(TestDataMixin, ViewTestCase):
    
    model = _models.band
    view_class = DuplicateObjectsView
    
    @classmethod
    def setUpTestData(cls):
        # Not using make() as the factory for band has band_name in get_or_create;
        # calling make(band_name = 'X') repeatedly will always return the same band object
        cls.test_data = [
            _models.band.objects.create(id = i, band_name = 'Beep')
            for i in range(1, 4)
        ]
        super().setUpTestData()
        
    def test_dispatch_sets_attrs(self):
        # Assert that dispatch sets model, opts, title, breadcrumbs_title from kwargs passed to dispatch
        request = self.get_request()
        view = self.get_view(request)
        view.dispatch(request, model_name = 'band')
        self.assertEqual(view.model, self.model)
        self.assertEqual(view.opts, self.model._meta)
        self.assertEqual(view.title, 'Duplikate: ' + self.model._meta.verbose_name)
        self.assertEqual(view.breadcrumbs_title, self.model._meta.verbose_name)
        
    def test_post_redirects_to_self_after_merging(self):
        # Assert that post redirects back to itself after a merge.
        # Upon completing a merge, MergeViewWizarded will return None.
        def mocked_as_view(*args, **kwargs):
            return Mock(return_value = None)
            
        path = reverse('dupes', kwargs = {'model_name': 'band'})
        request = self.post_request(path, data = {ACTION_CHECKBOX_NAME: ['1', '2']})
        view = self.get_view(request)
        view.model = self.model
            
        with patch.object(MergeViewWizarded, 'as_view', new = mocked_as_view):
            response = view.post(request)
            self.assertEqual(response.url, path)
        
    def test_post_calls_merge_view(self):
        # Assert that a post request will call the merge view.
        model_admin = utils.get_model_admin_for_model(self.model)
        request = self.post_request(data = {ACTION_CHECKBOX_NAME: ['1', '2']})
        view = self.get_view(request)
        view.model = self.model
        
        with patch.object(MergeViewWizarded, 'as_view') as mocked_as_view:
            view.post(request)
        self.assertEqual(mocked_as_view.call_count, 1)
        kwargs = mocked_as_view.call_args[1]
        self.assertIn('model_admin', kwargs)
        self.assertEqual(kwargs['model_admin'].__class__, model_admin.__class__)
        self.assertIn('queryset', kwargs)
        self.assertEqual(list(kwargs['queryset'].values_list('pk', flat = True)), [self.obj1.pk, self.obj2.pk])
        
    def test_post_does_not_call_merge_view_with_no_selects(self):
        # Assert that a post request will NOT call the merge view when no items in a sub list are selected for a merge.
        request = self.post_request(data = {ACTION_CHECKBOX_NAME: []})
        view = self.get_view(request)
        view.model = self.model
        
        with patch.object(MergeViewWizarded, 'as_view') as mocked_as_view:
            view.post(request)
        self.assertEqual(mocked_as_view.call_count, 0)
        
    def test_get_sets_dupe_fields(self):
        # Assert that the attribute dupe_fields is set correctly.
        pass
        
    def test_get_context_data_items(self):
        # Assert that the context item 'items' is built correctly.
        change_form_path = unquote(reverse('admin:DBentry_band_change', args=['{pk}']))
        link_template = '<a href="{url}">{name}</a>'
        
        request = self.get_request(data = {'fields':['band_name']})
        view = self.get_view(request)
        view.model = self.model
        view.opts = self.model._meta
        
        context = view.get_context_data()
        self.assertIn('items', context)
        items = context['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(len(items[0]), 2, 
            msg = "Should contain one set of duplicate objects and the url to their changelist.")
        self.assertEqual(len(items[0][0]), 3, 
            msg = "Should contain the three duplicate objects.")
        for dupe_item in items[0][0]:
            with self.subTest():
                self.assertEqual(len(dupe_item), 3)
                self.assertIsInstance(dupe_item[0], self.model, 
                    msg = "Should be one of duplicate objects.")
                expected_link = link_template.format(
                    url = change_form_path.format(pk = dupe_item[0].pk), 
                    name = str(dupe_item[0])
                )
                self.assertEqual(dupe_item[1], expected_link, 
                    msg = "Should be link to change form of object.")
                self.assertEqual(dupe_item[2], ['Beep'], 
                    msg = "Should be the duplicate object's values of the fields the duplicates were found with.")
        self.assertIsInstance(items[0][1], str, 
            msg = "Should be the url to the changelist of the duplicate objects.")
        self.assertIn('?', items[0][1], 
            msg = "Changelist url should be of format <changelist>?id__in=[ids]")
        cl_url, _ = items[0][1].split('?')
        self.assertEqual(cl_url, reverse('admin:DBentry_band_changelist'))
        
    def test_dupe_fields_prop(self):
        request = self.get_request(data = {'fields': ['beep', 'boop'], 'm2m_fields': ['baap']})
        view = self.get_view(request)
        self.assertEqual(view.dupe_fields, ['beep', 'boop', 'baap'])
        
        # dupe_fields uses request.GET, so a post request should return an empty list
        request = self.post_request(data = {'fields': ['beep', 'boop'], 'm2m_fields': ['baap']})
        view = self.get_view(request)
        self.assertEqual(view.dupe_fields, [])
