import re
from unittest.mock import Mock, patch

from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.forms import modelform_factory
from django.urls import NoReverseMatch

from dbentry.factory import make
from dbentry.utils import admin as admin_utils
from tests.case import RequestTestCase, add_urls
from tests.models import Audio, Band, Bestand, Lagerort, Musiker


class TestAdminUtils(RequestTestCase):
    model = Audio

    @classmethod
    def setUpTestData(cls):
        cls.musiker = make(Musiker, kuenstler_name='Robert Plant')
        cls.band = make(Band, band_name='Led Zeppelin')
        cls.obj1 = make(cls.model, titel='Testaudio')
        cls.obj2 = make(cls.model, titel='Hovercrafts')
        lagerort = make(Lagerort, ort="Aufm Tisch!")
        # noinspection PyUnresolvedReferences
        cls.bestand = make(Bestand, audio=cls.obj1, lagerort=lagerort)

        # noinspection PyUnresolvedReferences
        cls.test_data = [cls.obj1, cls.obj2]

        super().setUpTestData()

    ################################################################################################
    # test get_obj_link
    ################################################################################################

    def test_get_obj_link(self):
        """Assert that the expected link is returned by get_obj_link."""
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            self.assertEqual(
                admin_utils.get_obj_link(self.obj1, self.super_user),
                f'<a href="/admin/test_utils/audio/{self.obj1.pk}/change/">{self.obj1}</a>'
            )

    def test_get_obj_link_blank(self):
        """
        Assert that the expected link, with target="_blank", is returned by
        get_obj_link.
        """
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            self.assertEqual(
                admin_utils.get_obj_link(self.obj1, self.super_user, blank=True),
                f'<a href="/admin/test_utils/audio/{self.obj1.pk}/change/" '
                f'target="_blank">{self.obj1}</a>'
            )

    def test_get_obj_link_no_change_permission(self):
        """
        No link should be displayed, if the user does not have change
        permissions.
        """
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            # noinspection PyUnresolvedReferences
            self.assertEqual(
                admin_utils.get_obj_link(self.obj1, self.noperms_user),
                f"{self.model._meta.verbose_name}: {self.obj1}"
            )

    def test_get_obj_link_no_reverse_match(self):
        """
        No link should be displayed, if there is no reverse match for the given
        admin site name and model instance/model options.
        """
        # The test model 'Audio' is not registered with any admin sites.
        with self.assertNotRaises(NoReverseMatch):
            link = admin_utils.get_obj_link(self.obj1, self.super_user)
        # noinspection PyUnresolvedReferences
        self.assertEqual(link, f"{self.model._meta.verbose_name}: {self.obj1}")

    ################################################################################################
    # test link_list
    ################################################################################################

    def test_link_list(self):
        """Assert that the expected links are returned by link_list."""
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            links = admin_utils.link_list(self.get_request(), obj_list=[self.obj1, self.obj2])
        for i, (url, label) in enumerate(re.findall(r'<a href="(.*?)">(.*?)</a>', links)):
            with self.subTest(url=url, label=label):
                self.assertEqual(
                    url, '/admin/test_utils/audio/{}/change/'.format(self.test_data[i].pk)
                )
                self.assertEqual(label, str(self.test_data[i]))

    def test_link_list_blank(self):
        """
        Assert that all links returned by link_list have the target attribute
        set to "_blank".
        """
        sep = "§"  # use an unusual separator so the links can be split easily
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            links = admin_utils.link_list(
                self.get_request(), obj_list=[self.obj1, self.obj2], sep=sep, blank=True
            )
        for link in links.split(sep):
            with self.subTest(link=link):
                self.assertIn('target="_blank"', link)

    ################################################################################################
    # test get_changelist_link
    ################################################################################################

    def test_get_changelist_link(self):
        """Assert that the expected link is returned by get_changelist_link."""
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            self.assertEqual(
                admin_utils.get_changelist_link(self.model, self.super_user),
                '<a href="/admin/test_utils/audio/">Liste</a>'
            )

    def test_get_changelist_link_blank(self):
        """
        Assert that the expected link, with target="_blank", is returned by
        get_changelist_link.
        """
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            self.assertEqual(
                admin_utils.get_changelist_link(self.model, self.super_user, blank=True),
                '<a href="/admin/test_utils/audio/" target="_blank">Liste</a>'
            )

    ################################################################################################
    # test get_changelist_url
    ################################################################################################

    def test_get_changelist_url(self):
        """
        Check the output of get_changelist_url for various obj_list arguments.
        """
        # noinspection PyUnresolvedReferences
        obj2 = Audio.objects.create(titel='Any')
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            for obj_list in (None, [self.obj1], [self.obj1, obj2]):
                expected = '/admin/test_utils/audio/'
                if obj_list:
                    expected += "?id__in=" + ",".join([str(obj.pk) for obj in obj_list])
                with self.subTest(obj_list=obj_list):
                    self.assertEqual(
                        admin_utils.get_changelist_url(self.model, self.super_user, obj_list=obj_list),  # noqa
                        expected
                    )

    def test_get_changelist_url_no_perms(self):
        """
        Assert that get_changelist_url returns an empty string, if the user has
        no permission to access the requested changelist.
        """
        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
            self.assertEqual(admin_utils.get_changelist_url(self.model, self.noperms_user), "")

    def test_get_changelist_url_no_reverse(self):
        """
        Assert that get_changelist_url returns an empty string, if no reverse
        match could be found for the requested changelist.
        """

        class UnknownModel(models.Model):
            pass

        self.assertEqual(admin_utils.get_changelist_url(UnknownModel, self.super_user), "")

    def test_get_changelist_url_requires_change_or_view_perm(self):
        """
        Assert that either change or view permissions are needed for
        get_changelist_url to produce a URL.
        """
        ct = ContentType.objects.get_for_model(self.model)
        change = Permission.objects.get(codename='change_audio', content_type=ct)
        view = Permission.objects.get(codename='view_audio', content_type=ct)
        perms = [[], [change], [view], [change, view]]

        site = AdminSite()
        site.register(self.model, ModelAdmin)
        with add_urls(site.urls, 'admin/'):
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
                        self.assertEqual(url, '/admin/test_utils/audio/')

    ################################################################################################
    # test construct_change_message and _get_relation_change_message
    ################################################################################################

    def test_construct_change_message(self):
        # noinspection PyUnresolvedReferences
        m2m_musiker = self.obj1.musiker.through.objects.create(
            musiker=self.musiker, audio=self.obj1
        )
        # noinspection PyUnresolvedReferences
        m2m_band = self.obj1.band.through.objects.create(
            band=self.band, audio=self.obj1
        )

        form = modelform_factory(self.model, fields=['titel', 'tracks'])()
        form.changed_data = ['tracks']
        formsets = [
            Mock(new_objects=[m2m_musiker], changed_objects=[], deleted_objects=[]),
            Mock(changed_objects=[(self.bestand, ['lagerort'])], new_objects=[], deleted_objects=[]),  # noqa
            Mock(deleted_objects=[m2m_band], new_objects=[], changed_objects=[])
        ]

        msgs = admin_utils.construct_change_message(form, formsets, add=False)
        self.assertEqual(len(msgs), 4, msg="Expected four change messages.")
        form_msg, added_msg, changed_msg, deleted_msg = msgs
        self.assertEqual(
            form_msg['changed']['fields'], ['Anz. Tracks'],
            msg="Expected the label of the changed formfield to appear in 'fields'."
        )
        self.assertEqual(
            added_msg['added'],
            {'name': 'Audio-Musiker', 'object': 'Robert Plant'}
        )
        self.assertEqual(
            changed_msg['changed'],
            {'name': 'Bestand', 'object': 'Aufm Tisch!', 'fields': ['lagerort']}
        )
        self.assertEqual(deleted_msg['deleted'], {'name': 'Band', 'object': 'Led Zeppelin'})

    def test_construct_change_message_added(self):
        """
        If the supplied form has no changed_data, construct_change_message
        should return a simple 'added' change message.
        """
        msg = admin_utils.construct_change_message(Mock(changed_data=None), formsets=[], add=True)
        self.assertEqual(msg, [{'added': {}}])

    def test_get_relation_change_message_auto_created(self):
        """
        Assert that for relation changes via auto created m2m tables,
        _get_relation_change_message uses verbose name and object representation
        of the object at the other end of the m2m relation.
        """
        # noinspection PyUnresolvedReferences
        m2m = self.obj1.band.through.objects.create(band=self.band, audio=self.obj1)
        msg_dict = admin_utils._get_relation_change_message(m2m, parent_model=self.model)
        self.assertEqual(msg_dict['name'], 'Band')
        self.assertEqual(msg_dict['object'], 'Led Zeppelin')

    def test_get_relation_change_message(self):
        """
        Assert that _get_relation_change_message uses the m2m through table
        for the change message if that table is not auto created.
        """
        # noinspection PyUnresolvedReferences
        m2m = self.obj1.musiker.through.objects.create(musiker=self.musiker, audio=self.obj1)
        msg_dict = admin_utils._get_relation_change_message(m2m, parent_model=self.model)
        self.assertEqual(msg_dict['name'], 'Audio-Musiker')
        self.assertEqual(msg_dict['object'], 'Robert Plant')
        with patch.object(m2m._meta, 'verbose_name', new='Mocked!'):
            self.assertEqual(
                admin_utils._get_relation_change_message(m2m, parent_model=self.model)['name'],
                'Mocked!'
            )

    ################################################################################################
    # test AdminLog helper functions
    ################################################################################################

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
        # noinspection PyUnresolvedReferences
        m2m_band = self.obj1.band.through.objects.create(
            band=self.band, audio=self.obj1
        )
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
        # noinspection PyUnresolvedReferences
        m2m_band = self.obj1.band.through.objects.create(
            band=self.band, audio=self.obj1
        )
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

    ################################################################################################
    # test get_model_admin_for_model
    ################################################################################################

    def test_get_model_admin_for_model(self):
        """
        Assert that get_model_admin_for_model returns the expected ModelAdmin
        class.
        """
        site = AdminSite()
        model_admin_class = type('Dummy', (ModelAdmin,), {})
        # model_admin = ModelAdmin(self.model, site)
        site.register(self.model, model_admin_class)
        for arg in ('test_utils.Audio', self.model):
            with self.subTest(argument=arg):
                self.assertIsInstance(
                    admin_utils.get_model_admin_for_model(arg, site),
                    model_admin_class
                )

    def test_get_model_admin_for_model_not_registered(self):
        """
        get_model_admin_for_model should return None, if no ModelAdmin class
        is registered with the given model.
        """
        self.assertIsNone(admin_utils.get_model_admin_for_model('test_utils.Audio'), AdminSite())

    def test_get_model_admin_for_model_raises_lookup_error(self):
        """
        For unknown models, get_model_admin_for_model should raise a LookupError
        (through get_model_from_string).
        """
        with self.assertRaises(LookupError):
            admin_utils.get_model_admin_for_model('beepboop')
