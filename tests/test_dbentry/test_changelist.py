from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.views.main import ALL_VAR, ORDER_VAR
from django.db import models
from django.db.models.query import EmptyQuerySet
from django.test import override_settings
from django.urls import path

from dbentry.admin import admin as _admin
from dbentry import models as _models
from dbentry.admin.base import MIZModelAdmin
from dbentry.admin.changelist import MIZChangeList
from dbentry.admin.site import miz_site
from tests.case import AdminTestCase
from tests.model_factory import make

admin_site = AdminSite()


class ChangeListTestModel(models.Model):
    pass


@admin.register(ChangeListTestModel, site=admin_site)
class ChangeListTestAdmin(MIZModelAdmin):

    def get_changelist(self, request, **kwargs):
        return MIZChangeList


class URLConf:
    urlpatterns = [path('test_changelist/', admin_site.urls)]


@override_settings(ROOT_URLCONF=URLConf)
class TestMIZChangeList(AdminTestCase):
    admin_site = admin_site
    model = ChangeListTestModel
    model_admin_class = ChangeListTestAdmin

    def test_get_results_empty_when_unfiltered(self):
        """
        Assert that the result_list is an EmptyQuerySet if the changelist
        queryset is not filtered and the model admin has a search form.
        """
        request = self.get_request()
        changelist = self.model_admin.get_changelist_instance(request)
        with patch.object(self.model_admin, 'has_search_form', new=Mock(return_value=True)):
            changelist.get_results(request)
        self.assertIsInstance(changelist.result_list, EmptyQuerySet)

    def test_get_results_not_empty_when_filtered(self):
        """
        Assert that the result_list is not an EmptyQuerySet if the changelist
        queryset is filtered.
        """
        request = self.get_request(data={'id': '1'})
        changelist = self.model_admin.get_changelist_instance(request)
        with patch.object(self.model_admin, 'has_search_form', new=Mock(return_value=True)):
            changelist.get_results(request)
        self.assertNotIsInstance(changelist.result_list, EmptyQuerySet)

    def test_get_results_not_empty_when_no_search_form(self):
        """
        Assert that the result_list is not an EmptyQuerySet if the model admin
        has no search form. (even when the changelist queryset is unfiltered)
        """
        request = self.get_request()
        changelist = self.model_admin.get_changelist_instance(request)
        with patch.object(self.model_admin, 'has_search_form', new=Mock(return_value=False)):
            changelist.get_results(request)
        self.assertNotIsInstance(changelist.result_list, EmptyQuerySet)

    def test_get_results_not_empty_with_all_var(self):
        """
        Assert that the result_list is not an EmptyQuerySet if the ALL_VAR
        parameter is present in the request parameters.
        """
        request = self.get_request(data={ALL_VAR: '1'})
        changelist = self.model_admin.get_changelist_instance(request)
        changelist.get_results(request)
        self.assertNotIsInstance(changelist.result_list, EmptyQuerySet)

    def test_get_show_all_url(self):
        """Assert that get_show_all_url returns a query string that contains the ALL_VAR."""
        changelist = self.model_admin.get_changelist_instance(self.get_request())
        self.assertIn(ALL_VAR, changelist.get_show_all_url())


class TestAusgabeChangeList(AdminTestCase):
    admin_site = miz_site
    model = _models.Ausgabe
    model_admin_class = _admin.AusgabenAdmin

    @classmethod
    def setUpTestData(cls):
        make(cls.model)  # need at least one object for chronological_order
        super().setUpTestData()

    def test_get_queryset_ordering(self):
        """
        Assert that chronological order is not applied to the queryset if the
        ORDER_VAR is present in the query string.
        """
        for params in ({}, {ORDER_VAR: '1'}):
            with self.subTest(params=params):
                request = self.get_request(data=params)
                changelist = self.model_admin.get_changelist_instance(request=request)
                if params:
                    self.assertFalse(changelist.get_queryset(request).chronologically_ordered)
                else:
                    self.assertTrue(changelist.get_queryset(request).chronologically_ordered)


class TestBestandChangelist(AdminTestCase):
    admin_site = miz_site
    model = _models.Bestand
    model_admin_class = _admin.BestandAdmin

    def test_get_results_select_related(self):
        """
        Assert that the result_list uses select_related to include related
        object data in the queryset.
        """
        request = self.get_request()
        changelist = self.model_admin.get_changelist_instance(request)
        changelist.get_results(request)
        select_related = list(changelist.result_list.query.select_related)
        for field_path in (
                'audio', 'ausgabe', 'brochure', 'buch', 'dokument', 'foto',
                'memorabilien', 'plakat', 'technik', 'video',
                'lagerort', 'provenienz__geber'
        ):
            # Note that a path like provenienz__geber will be represented by a
            # nested dict in query.select_related: {'provenienz': {'geber': {}}}
            related = field_path.split('__', 1)[0]
            with self.subTest(relation_path=field_path):
                self.assertIn(related, select_related)
                select_related.remove(related)
        self.assertFalse(
            select_related,
            msg="Queryset unexpectedly selected additional related-object data."
        )
