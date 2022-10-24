from unittest import mock

from django import http
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from django.urls import path

from dbentry import models as _models
from dbentry.views import MIZSiteSearch, MIZ_permission_denied_view, SiteSearchView
from tests.case import ViewTestCase
from tests.factory import make
from .models import Artikel, Band, Genre, Musiker

admin_site = AdminSite(name='admin')


@admin.register(Band, Musiker, Genre, site=admin_site)
class Admin(admin.ModelAdmin):
    pass


class URLConf:
    urlpatterns = [path('test_views/', admin_site.urls)]


class TestPermissionDeniedView(ViewTestCase):

    def test_MIZ_permission_denied_view_missing_template(self):
        """
        Calling the view with an unknown template_name should return a
        'Forbidden' response.
        """
        # noinspection PyTypeChecker
        response = MIZ_permission_denied_view(None, None, template_name='beepboop')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(isinstance(response, http.HttpResponseForbidden))

    def test_MIZ_permission_denied_view_response_context(self):
        """
        The response context should contain the exception message and a boolean
        on whether this is a popup.
        """
        exception = PermissionDenied('Exception Text')
        response = MIZ_permission_denied_view(self.get_request(), exception)
        # noinspection PyUnresolvedReferences
        context = response.context_data
        self.assertTrue('exception' in context)
        self.assertEqual(context['exception'], 'Exception Text')
        self.assertTrue('is_popup' in context)


@override_settings(ROOT_URLCONF=URLConf)
class TestSiteSearchView(ViewTestCase):
    # noinspection PyPep8Naming
    class view_class(SiteSearchView):
        app_label = 'test_dbentry'  # use test models

        def _search(self, model, q):
            # noinspection PyUnresolvedReferences
            opts = model._meta
            field = ''
            if opts.model_name == 'band':
                field = 'band_name'
            elif opts.model_name == 'musiker':
                field = 'kuenstler_name'
            elif opts.model_name == 'genre':
                field = 'genre'
            if not field:
                return []
            # noinspection PyUnresolvedReferences
            return model.objects.filter(**{field + '__icontains': q})

    @classmethod
    def setUpTestData(cls):
        make(Musiker, kuenstler_name='Sharon Silva')
        super().setUpTestData()

    def test_get_result_list(self):
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertEqual(len(results), 1)
        self.assertIn('Musiker (1)', results[0])

    def test_get_result_list_no_perms(self):
        """
        Assert that get_result_list doesn't return changelist links for users
        who have no permission to view those changelists.
        """
        view = self.get_view(request=self.get_request(user=self.noperms_user))
        results = view.get_result_list('Silva')
        self.assertFalse(results)

    def test_get_result_list_no_changelist(self):
        """
        Assert that get_result_list doesn't return changelist links for models
        that do not have a registered ModelAdmin.
        """
        make(Artikel, schlagzeile='Silva everywhere!')  # no ModelAdmin for Artikel
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertEqual(len(results), 1)
        self.assertIn('Musiker (1)', results[0])

    def test_get_result_list_sorted(self):
        """
        Assert that the result list is sorted alphabetically by the models'
        object names.
        """
        make(Band, band_name='Silva')
        make(Genre, genre='Silva Music')
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertTrue(results)
        self.assertEqual(len(results), 3)
        self.assertIn('Bands (1)', results[0])
        self.assertIn('Genres (1)', results[1])
        self.assertIn('Musiker (1)', results[2])

    @mock.patch.object(SiteSearchView, 'render_to_response')
    def test_get(self, render_mock):
        """Assert that render_to_response is called with the expected context."""
        request = self.get_request(data={'q': 'Silva'})
        self.get_view(request).get(request)
        self.assertTrue(render_mock.called)
        context = render_mock.call_args[0][0]
        self.assertIn('q', context.keys())
        self.assertEqual(context['q'], 'Silva')
        self.assertIn('results', context.keys())
        results = context['results']
        self.assertTrue(results)
        self.assertEqual(len(results), 1)
        self.assertIn('?q=Silva', results[0])
        self.assertIn('Musiker (1)', results[0])

    @mock.patch.object(SiteSearchView, 'get_result_list')
    @mock.patch.object(SiteSearchView, 'render_to_response')
    def test_get_no_q(self, _render_mock, get_result_list_mock):
        """get_result_list should not be called when no search term was provided."""
        for data in ({}, {'q': ''}):
            with self.subTest(request_data=data):
                request = self.get_request(data=data)
                self.get_view(request).get(request)
                self.assertFalse(get_result_list_mock.called)


class TestMIZSiteSearch(ViewTestCase):
    view_class = MIZSiteSearch

    @classmethod
    def setUpTestData(cls):
        make(_models.Musiker, kuenstler_name='Sharon Silva')
        make(_models.Band, band_name='Silvas')
        make(_models.Veranstaltung, name='Silva Konzert')
        super().setUpTestData()

    def test_get_models_no_m2m_models(self):
        """Assert that _get_models filters out models subclassing BaseM2MModel."""
        view = self.get_view(self.get_request())
        models = view._get_models('dbentry')
        from dbentry.base.models import BaseModel, BaseM2MModel
        self.assertFalse(any(issubclass(m, BaseM2MModel) for m in models))
        self.assertTrue(all(issubclass(m, BaseModel) for m in models))

    def test_get_result_list(self):
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertTrue(results)
        self.assertEqual(len(results), 3)
        self.assertIn('Bands (1)', results[0])
        self.assertIn('Musiker (1)', results[1])
        self.assertIn('Veranstaltungen (1)', results[2])
