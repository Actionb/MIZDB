import re

from django.urls import NoReverseMatch
from django.utils.encoding import force_text

from DBentry import utils, models as _models
from DBentry.sites import miz_site
from DBentry.tests.base import RequestTestCase
from DBentry.tests.mixins import TestDataMixin


class TestAdminUtils(TestDataMixin, RequestTestCase):

    model = _models.Band
    test_data_count = 3
    opts = model._meta

    def test_get_obj_link_noperms(self):
        # Users without change permission should not get an edit link
        link = utils.get_obj_link(self.obj1, self.noperms_user)
        self.assertEqual(link, "{}: {}".format(self.opts.verbose_name, force_text(self.obj1)))

    def test_get_obj_link_noreversematch(self):
        # If there is no reverse match, no link should be displayed
        # get_obj_link uses the site_name argument to get the app's namespace
        with self.assertNotRaises(NoReverseMatch):
            link = utils.get_obj_link(self.obj1, self.super_user, site_name='BEEP BOOP')
        self.assertEqual(link, "{}: {}".format(self.opts.verbose_name, force_text(self.obj1)))

    def test_get_obj_link(self):
        link = utils.get_obj_link(self.obj1, self.super_user)
        url = '/admin/DBentry/band/{}/change/'.format(self.obj1.pk)
        expected = '<a href="{}">{}</a>'.format(url, force_text(self.obj1))
        self.assertEqual(link, expected)

        link = utils.get_obj_link(self.obj1, self.super_user, blank=True)
        url = '/admin/DBentry/band/{}/change/'.format(self.obj1.pk)
        expected = '<a href="{}" target="_blank">{}</a>'.format(url, force_text(self.obj1))
        self.assertEqual(link, expected)

    def test_link_list(self):
        request = self.get_request()
        links = utils.link_list(request, self.test_data)
        for i, (url, label) in enumerate(re.findall(r'<a href="(.*?)">(.*?)</a>', links)):
            self.assertEqual(
                url, '/admin/DBentry/band/{}/change/'.format(self.test_data[i].pk))
            self.assertEqual(label, str(self.test_data[i]))

    def test_link_list_blank(self):
        # Assert that all links contain target="_blank" when calling link_list
        # with blank=True.
        sep="§"  # use an unusual separator so the links can be split 'securily'
        links = utils.link_list(self.get_request(), self.test_data, sep=sep, blank=True)
        for link in links.split(sep):
            with self.subTest(link=link):
                self.assertIn('target="_blank"', link)

    def test_get_changelist_link(self):
        request = self.get_request()
        link = utils.get_changelist_link(_models.Artikel, request.user)
        self.assertEqual(link, '<a href="/admin/DBentry/artikel/">Liste</a>')
        link = utils.get_changelist_link(_models.Artikel, request.user, blank=True)
        self.assertEqual(link, '<a href="/admin/DBentry/artikel/" target="_blank">Liste</a>')

    def test_get_model_admin_for_model(self):
        from DBentry.admin import ArtikelAdmin
        self.assertIsInstance(utils.get_model_admin_for_model('Artikel'), ArtikelAdmin)
        self.assertIsInstance(utils.get_model_admin_for_model(_models.Artikel), ArtikelAdmin)
        self.assertIsNone(utils.get_model_admin_for_model('beepboop'))

    def test_has_admin_permission(self):
        from DBentry.admin import ArtikelAdmin, BildmaterialAdmin
        request = self.get_request(user=self.noperms_user)
        model_admin = ArtikelAdmin(_models.Artikel, miz_site)
        self.assertFalse(
            utils.has_admin_permission(request, model_admin),
            msg="Should return False for a user with no permissions."
        )

        from django.contrib.auth.models import Permission
        perms = Permission.objects.filter(codename__in=('add_artikel', ))
        self.staff_user.user_permissions.set(perms)
        request = self.get_request(user=self.staff_user)
        model_admin = ArtikelAdmin(_models.Artikel, miz_site)
        self.assertTrue(
            utils.has_admin_permission(request, model_admin),
            msg=(
                "Should return True for a user with at least some permissions "
                "for that model admin."
            )
        )

        request = self.get_request(user=self.staff_user)
        model_admin = BildmaterialAdmin(_models.bildmaterial, miz_site)
        self.assertFalse(
            utils.has_admin_permission(request, model_admin),
            msg="Should return False for non-superusers on a superuser only model admin."
        )

        request = self.get_request(user=self.super_user)
        model_admin = BildmaterialAdmin(_models.bildmaterial, miz_site)
        self.assertTrue(
            utils.has_admin_permission(request, model_admin),
            msg="Should return True for superuser on a superuser-only model admin."
        )
