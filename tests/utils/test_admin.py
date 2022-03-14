import re
from unittest.mock import patch, Mock

from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.forms import modelform_factory
from django.urls import NoReverseMatch
from django.utils.encoding import force_str

from dbentry import models as _models, admin as _admin
from dbentry.factory import make
from dbentry.sites import miz_site
from tests.case import RequestTestCase
from dbentry.tests.mixins import TestDataMixin
from dbentry.utils import admin as admin_utils


class TestAdminUtils(RequestTestCase):
    model = _models.Audio

    @classmethod
    def setUpTestData(cls):
        cls.musiker = make(_models.Musiker, kuenstler_name='Robert Plant')
        cls.band = make(_models.Band, band_name='Led Zeppelin')
        cls.obj1 = make(cls.model, titel='Testaudio')
        cls.obj2 = make(cls.model, titel='TODO')
        lagerort = make(_models.Lagerort, ort="Aufm Tisch!")
        cls.bestand = make(_models.Bestand, audio=cls.obj1, lagerort=lagerort)

        cls.test_data = [cls.obj1, cls.obj2]

        super().setUpTestData()

    ################################################################################################
    # test get_obj_link
    ################################################################################################

    def test_get_obj_link(self):
        """Assert that the expected link is returned by get_obj_link."""
        self.assertEqual(
            admin_utils.get_obj_link(self.obj1, self.super_user),
            f'<a href="/admin/dbentry/audio/{self.obj1.pk}/change/">{self.obj1}</a>'
        )

    def test_get_obj_link_blank(self):
        """
        Assert that the expected link, with target="_blank", is returned by
        get_obj_link.
        """
        self.assertEqual(
            admin_utils.get_obj_link(self.obj1, self.super_user, blank=True),
            f'<a href="/admin/dbentry/audio/{self.obj1.pk}/change/" target="_blank">{self.obj1}</a>'
        )

    def test_get_obj_link_no_change_permission(self):
        """
        No link should be displayed, if the user does not have change
        permissions.
        """
        link = admin_utils.get_obj_link(self.obj1, self.noperms_user)
        self.assertEqual(link, f"{self.model._meta.verbose_name}: {self.obj1}")

    def test_get_obj_link_noreversematch(self):
        """
        No link should be displayed, if there is no reverse match for the given
        admin site name and model instance/model options.
        """
        # get_obj_link uses the site_name argument to get the app's URL namespace
        with self.assertNotRaises(NoReverseMatch):
            link = admin_utils.get_obj_link(self.obj1, self.super_user, site_name='BEEP BOOP')
        self.assertEqual(link, f"{self.model._meta.verbose_name}: {self.obj1}")

    ################################################################################################
    # test link_list
    ################################################################################################

    def test_link_list(self):
        """Assert that the expected links are returned by link_list."""
        links = admin_utils.link_list(self.get_request(), obj_list=[self.obj1, self.obj2])
        for i, (url, label) in enumerate(re.findall(r'<a href="(.*?)">(.*?)</a>', links)):
            with self.subTest(url=url, label=label):
                self.assertEqual(
                    url, '/admin/dbentry/audio/{}/change/'.format(self.test_data[i].pk))
                self.assertEqual(label, str(self.test_data[i]))

    def test_link_list_blank(self):
        """
        Assert that all links returned by link_list have the target attribute
        set to "_blank".
        """
        sep = "§"  # use an unusual separator so the links can be split easily
        links = admin_utils.link_list(
            self.get_request(), obj_list=[self.obj1, self.obj2], sep=sep, blank=True)
        for link in links.split(sep):
            with self.subTest(link=link):
                self.assertIn('target="_blank"', link)

    ################################################################################################
    # test get_changelist_link
    ################################################################################################

    def test_get_changelist_link(self):
        """Assert that the expected link is returned by get_changelist_link."""
        self.assertEqual(
            admin_utils.get_changelist_link(_models.Artikel, self.super_user),
            '<a href="/admin/dbentry/artikel/">Liste</a>'
        )

    def test_get_changelist_link_blank(self):
        """
        Assert that the expected link, with target="_blank", is returned by
        get_changelist_link.
        """
        self.assertEqual(
            admin_utils.get_changelist_link(_models.Artikel, self.super_user, blank=True),
            '<a href="/admin/dbentry/artikel/" target="_blank">Liste</a>'
        )

    ################################################################################################
    # test get_changelist_url
    ################################################################################################

    def test_get_changelist_url(self):
        """
        Check the output of get_changelist_url for various obj_list arguments.
        """
        obj2 = make(self.model)
        for obj_list in (None, [self.obj1], [self.obj1, obj2]):
            expected = '/admin/dbentry/audio/'
            if obj_list:
                expected += "?id__in=" + ",".join([str(obj.pk) for obj in obj_list])
            with self.subTest(obj_list=obj_list):
                self.assertEqual(
                    admin_utils.get_changelist_url(self.model, self.super_user, obj_list=obj_list),
                    expected
                )

    def test_get_changelist_url_no_perms(self):
        """
        Assert that get_changelist_url returns an empty string, if the user has
        no permission to access the requested changelist.
        """
        self.assertEqual(admin_utils.get_changelist_url(self.model, self.noperms_user), "")

    def test_get_changelist_url_no_reverse(self):
        """
        Assert that get_changelist_url returns an empty string, if no reverse
        match could be found for the requested changelist.
        """
        # TODO: replace model argument with a test-only model
        self.assertEqual(admin_utils.get_changelist_url(_models.BaseBrochure, self.super_user), "")

    def test_get_changelist_url_requires_change_or_view_perm(self):
        """
        Assert that either change or view permissions are needed for
        get_changelist_url to produce a URL.
        """
        change = Permission.objects.get(codename='change_audio')
        view = Permission.objects.get(codename='view_audio')
        perms = [[], [change], [view], [change, view]]
        for permissions in perms:
            with self.subTest(permissions=permissions):
                self.staff_user.user_permissions.set(permissions)
                # Re-fetch the user from the database to reset the permission cache:
                # https://docs.djangoproject.com/en/3.2/topics/auth/default/#permission-caching
                user = get_user_model().objects.get(pk=self.staff_user.pk)
                url = admin_utils.get_changelist_url(model=self.model, user=user)
                if not permissions:
                    self.assertFalse(url)
                else:
                    self.assertEqual(url, '/admin/dbentry/audio/')

    # TODO: @work: start here
    def test_get_model_admin_for_model(self):
        self.assertIsInstance(admin_utils.get_model_admin_for_model('Artikel'), _admin.ArtikelAdmin)
        self.assertIsInstance(admin_utils.get_model_admin_for_model(_models.Artikel), _admin.ArtikelAdmin)
        with self.assertRaises(LookupError):
            admin_utils.get_model_admin_for_model('beepboop')

    def test_has_admin_permission(self):
        request = self.get_request(user=self.noperms_user)
        model_admin = _admin.ArtikelAdmin(_models.Artikel, miz_site)
        self.assertFalse(
            admin_utils.has_admin_permission(request, model_admin),
            msg="Should return False for a user with no permissions."
        )

        perms = Permission.objects.filter(codename__in=('add_artikel',))
        self.staff_user.user_permissions.set(perms)
        request = self.get_request(user=self.staff_user)
        model_admin = _admin.ArtikelAdmin(_models.Artikel, miz_site)
        self.assertTrue(
            admin_utils.has_admin_permission(request, model_admin),
            msg=(
                "Should return True for a user with at least some permissions "
                "for that model admin."
            )
        )

        request = self.get_request(user=self.staff_user)
        model_admin = _admin.PlakatAdmin(_models.Plakat, miz_site)
        self.assertFalse(
            admin_utils.has_admin_permission(request, model_admin),
            msg="Should return False for non-superusers on a superuser only model admin."
        )

        request = self.get_request(user=self.super_user)
        model_admin = _admin.PlakatAdmin(_models.Plakat, miz_site)
        self.assertTrue(
            admin_utils.has_admin_permission(request, model_admin),
            msg="Should return True for superuser on a superuser-only model admin."
        )

    def test_get_relation_change_message_auto_created(self):
        # Assert that _get_relation_change_message uses the Band model
        # instead of the auto created m2m through table for the change message.
        m2m = self.obj1.band.through.objects.create(
            band=self.band, audio=self.obj1)
        msg_dict = admin_utils._get_relation_change_message(m2m, parent_model=self.model)
        self.assertEqual(msg_dict['name'], 'Band')
        self.assertEqual(msg_dict['object'], 'Led Zeppelin')

    def test_get_relation_change_message(self):
        # Assert that _get_relation_change_message uses the m2m through table
        # for the change message if that table is not auto created.
        m2m = self.obj1.musiker.through.objects.create(
            musiker=self.musiker, audio=self.obj1)
        msg_dict = admin_utils._get_relation_change_message(m2m, parent_model=self.model)
        self.assertEqual(msg_dict['name'], 'Audio-Musiker')
        self.assertEqual(msg_dict['object'], 'Robert Plant')
        with patch.object(m2m._meta, 'verbose_name', new='Mocked!'):
            self.assertEqual(
                admin_utils._get_relation_change_message(m2m, parent_model=self.model)['name'],
                'Mocked!'
            )

    def test_construct_change_message(self):
        form = modelform_factory(self.model, fields=['titel', 'tracks'])()
        form.changed_data = ['tracks']

        m2m_musiker = self.obj1.musiker.through.objects.create(
            musiker=self.musiker, audio=self.obj1)
        m2m_band = self.obj1.band.through.objects.create(
            band=self.band, audio=self.obj1)

        formsets = [
            Mock(new_objects=[m2m_musiker], changed_objects=[], deleted_objects=[]),
            Mock(changed_objects=[(self.bestand, ['lagerort'])], new_objects=[], deleted_objects=[]),
            Mock(deleted_objects=[m2m_band], new_objects=[], changed_objects=[])
        ]

        msgs = admin_utils.construct_change_message(form, formsets, add=False)
        self.assertEqual(len(msgs), 4)
        form_msg, added_msg, changed_msg, deleted_msg = msgs
        self.assertEqual(
            form_msg['changed']['fields'], ['Anz. Tracks'],
            msg="Expected the label of the changed formfield to appear in 'fields'."
        )
        self.assertEqual(added_msg['added'], {'name': 'Audio-Musiker', 'object': 'Robert Plant'}),
        self.assertEqual(
            changed_msg['changed'],
            {'name': 'Bestand', 'object': 'Aufm Tisch!', 'fields': ['lagerort']}
        )
        self.assertEqual(deleted_msg['deleted'], {'name': 'Band', 'object': 'Led Zeppelin'})

    def test_construct_change_message_added(self):
        msg = admin_utils.construct_change_message(Mock(changed_data=None), formsets=[], add=True)
        self.assertEqual(msg, [{'added': {}}])

    def test_log_addition(self):
        with patch('dbentry.utils.admin.create_logentry') as mocked_create_logentry:
            admin_utils.log_addition(
                user_id=self.super_user.pk,
                obj=self.obj1,
                related_obj=None,
            )
            expected_message = [{'added': {}}]
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag, message = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, ADDITION)
            self.assertIsInstance(message, list)
            self.assertEqual(message, expected_message)

    def test_log_addition_related_obj(self):
        m2m_band = self.obj1.band.through.objects.create(
            band=self.band, audio=self.obj1)
        with patch('dbentry.utils.admin.create_logentry') as mocked_create_logentry:
            admin_utils.log_addition(
                user_id=self.super_user.pk,
                obj=self.obj1,
                related_obj=m2m_band,
            )
            expected_message = [{'added': {'name': 'Band', 'object': 'Led Zeppelin'}}]
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag, message = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, ADDITION)
            self.assertIsInstance(message, list)
            self.assertEqual(message, expected_message)

    def test_log_change(self):
        with patch('dbentry.utils.admin.create_logentry') as mocked_create_logentry:
            admin_utils.log_change(
                user_id=self.super_user.pk,
                obj=self.obj1,
                fields=['titel'],
                related_obj=None,
            )
            expected_message = [{'changed': {'fields': ['Titel']}}]
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag, message = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, CHANGE)
            self.assertIsInstance(message, list)
            self.assertEqual(message, expected_message)

    def test_log_change_related_obj(self):
        # Note: to understand the purpose of logging changes of related objects,
        # imagine logging changes to admin inlines.
        m2m_band = self.obj1.band.through.objects.create(
            band=self.band, audio=self.obj1)
        with patch('dbentry.utils.admin.create_logentry') as mocked_create_logentry:
            admin_utils.log_change(
                user_id=self.super_user.pk,
                obj=self.obj1,
                fields=['band'],
                related_obj=m2m_band,
            )
            expected_message = [
                {'changed': {'fields': ['Band'], 'name': 'Band', 'object': 'Led Zeppelin'}}]
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag, message = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, CHANGE)
            self.assertIsInstance(message, list)
            self.assertEqual(message, expected_message)

    def test_log_deletion(self):
        with patch('dbentry.utils.admin.create_logentry') as mocked_create_logentry:
            admin_utils.log_deletion(user_id=self.super_user.pk, obj=self.obj1)
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, DELETION)
