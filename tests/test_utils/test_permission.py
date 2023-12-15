from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from dbentry.utils.permission import (
    has_change_permission, has_delete_permission,
    has_view_permission
)
from tests.case import UserTestCase, DataTestCase
from .models import Band


class TestPermissions(DataTestCase, UserTestCase):
    model = Band

    def setUp(self):
        super().setUp()
        self.opts = self.model._meta
        self.content_type = ContentType.objects.get_for_model(Band)
        self.user = self.staff_user

    def add_permission(self, action):
        perm = Permission.objects.get(
            codename=get_permission_codename(action, self.opts),
            content_type=self.content_type
        )
        self.user.user_permissions.add(perm)
        self.user = self.reload_user(self.user)

    def test_has_change_permission(self):
        self.assertFalse(has_change_permission(self.user, self.opts))
        self.add_permission('change')
        self.assertTrue(has_change_permission(self.user, self.opts))

    def test_has_delete_permission(self):
        self.assertFalse(has_delete_permission(self.user, self.opts))
        self.add_permission('delete')
        self.assertTrue(has_delete_permission(self.user, self.opts))

    @override_settings(ANONYMOUS_CAN_VIEW=False)
    def test_has_view_permission(self):
        # Should return True with either view or change permission (or both).
        self.assertFalse(has_view_permission(self.user, self.opts))
        self.add_permission('view')
        self.assertTrue(has_view_permission(self.user, self.opts))

        # Reset permissions:
        self.user.user_permissions.set([])
        self.user = self.reload_user(self.user)
        self.assertFalse(has_view_permission(self.user, self.opts))

        self.add_permission('change')
        self.assertTrue(has_view_permission(self.user, self.opts))
        self.add_permission('view')
        self.assertTrue(has_view_permission(self.user, self.opts))

    @override_settings(ANONYMOUS_CAN_VIEW=True)
    def test_has_view_permission_anonymous(self):
        """
        Assert that has_view_permission returns true if ANONYMOUS_CAN_VIEW
        setting is True.
        """
        self.assertTrue(has_view_permission(self.user, self.opts))
        self.assertTrue(has_view_permission(AnonymousUser(), self.opts))