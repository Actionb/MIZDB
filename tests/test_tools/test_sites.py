from unittest import expectedFailure
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.test import override_settings
from django.urls import path, reverse
from django.views import View

from dbentry.tools.sites import SiteToolMixin
from tests.case import RequestTestCase
from .models import Band, Musiker


class DummySite(SiteToolMixin, admin.AdminSite):
    pass


class DummyTool(View):
    pass


admin_site = DummySite()


class URLConf:
    urlpatterns = [
        path('test_changelist/', admin_site.urls),
        path('dummy_tool/', DummyTool.as_view(), name='dummy_tool')
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestSiteToolMixin(RequestTestCase):
    """Test the tools site mixin."""
    # Items in the tools list are a 5-tuple:
    #   (tool, url_name, index_label, permission_required, superuser_only)

    site = admin_site

    @patch("dbentry.sites.admin.AdminSite.check")
    def test_check(self, super_mock):
        """Assert that check() adds errors if an url name cannot be reversed."""
        super_mock.return_value = []
        with patch.object(self.site, 'tools', new=[]):
            # No tools, no errors:
            self.assertFalse(self.site.check(None))
            # The site's index is a reversible url name:
            self.site.tools = [(None, f"{self.site.name}:index", '', (), False)]
            self.assertFalse(self.site.check(None))
            # Add a tool with a bogus url name:
            self.site.tools.append((None, '404_url', '', (), False))
            errors = self.site.check(None)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)

    def test_register_tool(self):
        """Assert that register_tool() appends tools to the tools list."""
        self.assertFalse(self.site.tools)
        tool = ('view class', 'url name', 'label', ('test_tools.add_band',), False)
        with patch.object(self.site, 'tools', new=[]):
            self.site.register_tool(*tool)
            self.assertIn(tool, self.site.tools)

    @expectedFailure
    def test_build_admintools_context_permission_required(self):
        """
        Assert that build_admintools_context() excludes tools if the user does
        not have all the required permissions.
        """
        band_codename = get_permission_codename('add', Band._meta)
        musiker_codename = get_permission_codename('add', Musiker._meta)
        perms_required = (f"test_tools.{band_codename}", f"test_tools.{musiker_codename}")
        request = self.get_request(user=self.staff_user)

        tool = (None, '', '', perms_required, False)
        with patch.object(self.site, 'tools', new=[tool]):
            self.assertFalse(self.site.build_admintools_context(request))

            # Add band permission:
            ct = ContentType.objects.get_for_model(Band)
            self.staff_user.user_permissions.add(
                Permission.objects.get(codename=band_codename, content_type=ct)
            )
            self.assertFalse(self.site.build_admintools_context(request))

            # Add musiker permission:
            ct = ContentType.objects.get_for_model(Musiker)
            self.staff_user.user_permissions.add(
                Permission.objects.get(codename=musiker_codename, content_type=ct)
            )
            self.assertTrue(self.site.build_admintools_context(request))

    def test_build_admintools_context_superuser_only(self):
        """
        Assert that build_admintools_context() excludes tools flagged with
        superuser_only=True if the user is not a superuser.
        """
        tool = (None, '', '', (), True)
        with patch.object(self.site, 'tools', new=[tool]):
            request = self.get_request(user=self.super_user)
            self.assertTrue(self.site.build_admintools_context(request))
            request = self.get_request(user=self.noperms_user)
            self.assertFalse(self.site.build_admintools_context(request))

    def test_index_adds_admintools_to_context(self):
        """Assert that the admintools are added to the index context."""
        tool = ('view class', 'dummy_tool', 'label', ('test_tools.add_band',), False)
        with patch.object(self.site, 'tools', new=[tool]):
            response = self.get_response(reverse(f'{self.site.name}:index'))
            self.assertIn('admintools', response.context_data)
            tools = response.context_data.get('admintools')
            self.assertIn('dummy_tool', tools)
            self.assertEqual(tools['dummy_tool'], 'label')
