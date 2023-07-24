import json
import re
from unittest.mock import patch

from django import forms
from django.test import override_settings
from django.urls import path, reverse
from django.views import View

from dbentry.site.views.base import BaseEditView
from tests.case import ViewTestCase, DataTestCase
from tests.model_factory import make
from .models import Foo


class ViewTestMixin:

    def test(self):
        pass


class DummySite:
    model_list = 'dummy_model_list'


class FooView(BaseEditView):
    model = Foo
    form_class = forms.modelform_factory(Foo, fields=forms.ALL_FIELDS)
    site = DummySite()


class ChangelistView(View):
    pass


class URLConf:
    app_name = 'test_site'
    urlpatterns = [
        path('add/', FooView.as_view(extra_context={'add': True}), name='test_site_foo_add'),
        path('<path:object_id>/change/', FooView.as_view(extra_context={'add': False}), name='test_site_foo_change'),
        path('changelist/', ChangelistView.as_view(), name='test_site_foo_changelist')
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestBaseEditView(DataTestCase, ViewTestCase):
    model = Foo
    view_class = FooView

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(Foo)
        super().setUpTestData()

    def test_get_context_data(self):
        for add in (True, False):
            with self.subTest(add=add):
                kwargs = {'extra_context': {'add': add}}
                if not add:
                    kwargs['kwargs'] = {'object_id': self.obj.pk}
                view = self.get_view(self.get_request(), **kwargs)
                view.object = view.get_object()

                ctx = view.get_context_data()
                test_data = [
                    ('model', self.model),
                    ('opts', self.model._meta),
                    ('add', add),
                    ('title', 'Foo hinzufügen' if add else 'Foo ändern'),
                    ("popup_links", True)
                ]
                for k, v in test_data:
                    with self.subTest(key=k):
                        self.assertIn(k, ctx)
                        self.assertEqual(ctx[k], v)

    def test_get_object(self):
        """
        If not currently adding a new model object, get_object should return
        the model object of the form.
        """
        view = self.get_view(kwargs={'object_id': self.obj.pk}, extra_context={'add': False})
        self.assertEqual(view.get_object(), self.obj)
        view = self.get_view(extra_context={'add': True})
        self.assertFalse(view.get_object())

    def test_get_success_url(self):
        """
        The success url should return the 'changelist' URL after clicking the
        'add' submit button (basic save button).
        """
        for is_add in (True, False):
            if is_add:
                request = self.get_request(reverse('test_site_foo_add'))
            else:
                request = self.get_request(reverse('test_site_foo_change', args=[self.obj.pk]))
            for submit_btn_extra_data in ('', 'add'):
                with self.subTest(add=is_add, extra_data=submit_btn_extra_data):
                    view = self.get_view(request, extra_context={'add': is_add})
                    with patch.object(view, 'get_extra_data') as extra_data_mock:
                        extra_data_mock.return_value = {submit_btn_extra_data: True}
                        self.assertEqual(view.get_success_url(), reverse('test_site_foo_changelist'))

    def test_get_success_url_add_another(self):
        """
        The success url should return the 'add' URL after clicking the
        'add another' submit button.
        """
        for is_add in (True, False):
            if is_add:
                request = self.get_request(reverse('test_site_foo_add'))
            else:
                request = self.get_request(reverse('test_site_foo_change', args=[self.obj.pk]))
            with self.subTest(add=is_add):
                view = self.get_view(request, extra_context={'add': is_add})
                with patch.object(view, 'get_extra_data') as extra_data_mock:
                    extra_data_mock.return_value = {'add_another': True}
                    self.assertEqual(view.get_success_url(), reverse('test_site_foo_add'))

    def test_get_success_url_continue(self):
        """
        The success url should return the 'change' URL of the saved object after
        clicking the 'continue' submit button.
        """
        for is_add in (True, False):
            if is_add:
                request = self.get_request(reverse('test_site_foo_add'))
            else:
                request = self.get_request(reverse('test_site_foo_change', args=[self.obj.pk]))
            with self.subTest(add=is_add):
                view = self.get_view(request, extra_context={'add': is_add})
                with patch.object(view, 'get_extra_data') as extra_data_mock:
                    extra_data_mock.return_value = {'continue': True}
                    with patch.object(view, 'object', new=self.obj, create=True):
                        self.assertEqual(view.get_success_url(), reverse('test_site_foo_change', args=[self.obj.pk]))

    def test_form_valid_add(self):
        """
        The user should be redirected back to the model's changelist after
        having submitted a valid form via the 'add' button.
        """
        response = self.post_response(
            reverse('test_site_foo_add'),
            data=json.dumps({'formset_data': {'bar': 42}, '_extra': {'add': True}}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertIn('success_url', response_json)
        self.assertEqual(
            response_json['success_url'],
            reverse('test_site_foo_changelist')
        )

    def test_form_valid_add_another(self):
        """
        The user should be redirected to another view with an empty form after
        having submitted a valid form via the 'add another' button.
        """
        response = self.post_response(
            reverse('test_site_foo_add'),
            data=json.dumps({'formset_data': {'bar': 42}, '_extra': {'add_another': True}}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertIn('success_url', response_json)
        self.assertEqual(
            response_json['success_url'],
            reverse('test_site_foo_add')
        )

    def test_form_valid_continue(self):
        """
        When submitting a valid form via the 'continue' button, the form should
        be saved and be displayed again for further changes.
        """
        response = self.post_response(
            reverse('test_site_foo_add'),
            data=json.dumps({'formset_data': {'bar': 42}, '_extra': {'continue': True}}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertIn('success_url', response_json)
        # We don't know the id of the saved object.
        # Reverse a change page with a placeholder id, then check against a
        # regex with the placeholder replaced with the '\d' pattern.
        change_url = reverse("test_site_foo_change", args=[999])
        regex = re.compile(re.sub('999', r'\\d+', change_url))
        self.assertRegex(response_json['success_url'], regex)
