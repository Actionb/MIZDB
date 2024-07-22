from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.test import override_settings
from django.urls import reverse, path
from django.views import View

from dbentry import models as _models
from dbentry.admin.base import MIZModelAdmin
from dbentry.admin.site import MIZAdminSite, miz_site
from tests.case import RequestTestCase
from tests.test_dbentry.models import Band, Musiker

miz_admin_site = MIZAdminSite()


class DummyTool(View):
    pass


# Must register with a model from the 'dbentry' app, since some of the  methods
# of MIZAdminSite look for the 'dbentry' app specifically.
@admin.register(_models.Artikel, site=miz_admin_site)
class ArtikelAdmin(MIZModelAdmin):
    index_category = "Archivgut"


class URLConf:
    urlpatterns = [
        path("admin/", miz_admin_site.urls),
        path("dummy_tool/", DummyTool.as_view(), name="dummy_tool"),
        path("", View.as_view(), name="index")
    ]


class TestMIZAdminSite(RequestTestCase):
    """Test the base admin site class MIZAdminSite."""

    site = miz_admin_site

    @patch("dbentry.admin.site.super")
    def test_app_index_returns_dbentry(self, super_mock):
        """
        Assert that a request for the app index of app 'dbentry' returns the
        main admin index (which would include the fake apps).
        """
        for app_label, index_called in [("dbentry", True), ("Beep", False)]:
            with self.subTest(app_label=app_label):
                with patch.object(self.site, "index") as index_mock:
                    self.site.app_index(request=None, app_label=app_label)  # noqa
                    if index_called:
                        self.assertTrue(index_mock.called)
                        self.assertFalse(super_mock.called)
                    else:
                        self.assertFalse(index_mock.called)
                        self.assertTrue(super_mock.called)

    def test_app_index_categories(self):
        """
        Assert that the dbentry app_list contains the additional 'fake' apps
        that organize the various models of the app.
        """
        request = self.get_request(path=reverse("admin:index"))
        response = self.site.app_index(request, app_label="dbentry")
        app_list = response.context_data["app_list"]  # noqa
        app_names = [d.get("name") for d in app_list if d.get("name")]
        for category in ["Archivgut", "Stammdaten", "Sonstige"]:
            with self.subTest():
                self.assertIn(category, app_names)

    def test_add_categories_no_category(self):
        """
        Assert that add_categories puts ModelAdmins with a category that isn't
        one of the three default ones (Archivgut, Stammdaten, Sonstige) into
        the 'Sonstige' category.
        """
        for index_category in ("Sonstige", "Beep", None):
            app_list = [{"app_label": "dbentry", "models": [{"object_name": "Artikel"}]}]
            with self.subTest(index_category=str(index_category)):
                with patch.object(ArtikelAdmin, "index_category", new=index_category):
                    app_list = self.site.add_categories(app_list)
                    self.assertEqual(len(app_list), 3, app_list)
                    self.assertEqual(app_list[-1]["name"], "Sonstige")
                    sonstige_category = app_list[-1]
                    self.assertEqual(len(sonstige_category["models"]), 1)
                    self.assertEqual(sonstige_category["models"][0]["object_name"], "Artikel")

    def test_add_categories_no_dbentry_app(self):
        """
        Assert that add_categories returns an empty list if no 'dbentry' app
        can be found in the given app_list.
        """
        app_list = []
        self.assertFalse(self.site.add_categories(app_list))
        app_list.append({"app_label": "Beep", "models": []})
        self.assertFalse(self.site.add_categories(app_list))
        app_list.append({"app_label": "dbentry", "models": []})
        self.assertTrue(self.site.add_categories(app_list))

    @patch("dbentry.admin.site.super")
    def test_check(self, super_mock):
        """Assert that check() adds errors if an url name cannot be reversed."""
        super_mock.return_value.check.return_value = []
        with patch.object(self.site, "tools", new=[]):
            # No tools, no errors:
            self.assertFalse(self.site.check(None))
            # The site's index is a reversible url name:
            self.site.tools = [(None, f"{self.site.name}:index", "", (), False)]
            self.assertFalse(self.site.check(None))
            # Add a tool with a bogus url name:
            self.site.tools.append((None, "404_url", "", (), False))
            errors = self.site.check(None)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)

    def test_register_tool(self):
        """Assert that register_tool() appends tools to the tools list."""
        self.assertFalse(self.site.tools)
        tool = ("view class", "url name", "label", ("test_dbentry.add_band",), False)
        with patch.object(self.site, "tools", new=[]):
            self.site.register_tool(*tool)
            self.assertIn(tool, self.site.tools)

    def test_build_admintools_context_permission_required(self):
        """
        Assert that build_admintools_context() excludes tools if the user does
        not have all the required permissions.
        """
        band_codename = get_permission_codename("add", Band._meta)
        musiker_codename = get_permission_codename("add", Musiker._meta)
        perms_required = (f"{Band._meta.app_label}.{band_codename}", f"{Musiker._meta.app_label}.{musiker_codename}")
        request = self.get_request(user=self.staff_user)

        tool = (None, "", "", perms_required, False)
        with patch.object(self.site, "tools", new=[tool]):
            self.assertFalse(self.site.build_admintools_context(request))

            # Add band permission:
            ct = ContentType.objects.get_for_model(Band)
            self.staff_user.user_permissions.add(Permission.objects.get(codename=band_codename, content_type=ct))
            request.user = self.reload_user(self.staff_user)
            self.assertFalse(self.site.build_admintools_context(request))

            # Add musiker permission:
            ct = ContentType.objects.get_for_model(Musiker)
            self.staff_user.user_permissions.add(Permission.objects.get(codename=musiker_codename, content_type=ct))
            request.user = self.reload_user(self.staff_user)
            self.assertTrue(self.site.build_admintools_context(request))

    def test_build_admintools_context_superuser_only(self):
        """
        Assert that build_admintools_context() excludes tools flagged with
        superuser_only=True if the user is not a superuser.
        """
        tool = (None, "", "", (), True)
        with patch.object(self.site, "tools", new=[tool]):
            request = self.get_request(user=self.super_user)
            self.assertTrue(self.site.build_admintools_context(request))
            request = self.get_request(user=self.noperms_user)
            self.assertFalse(self.site.build_admintools_context(request))

    @override_settings(ROOT_URLCONF=URLConf)
    def test_index_adds_admintools_to_context(self):
        """Assert that the admintools are added to the index context."""
        # Items in the tools list are a 5-tuple:
        #   (tool, url_name, index_label, permission_required, superuser_only)
        tool = ("view class", "dummy_tool", "label", ("test_dbentry.add_band",), False)
        with patch.object(self.site, "tools", new=[tool]):
            response = self.get_response(reverse(f"{self.site.name}:index"))
            self.assertIn("admintools", response.context_data)
            tools = response.context_data.get("admintools")
            self.assertIn("dummy_tool", tools)
            self.assertEqual(tools["dummy_tool"], "label")


class TestMIZSite(RequestTestCase):
    """Test the admin site 'miz_site'."""

    def test_index_tools_superuser(self):
        """Check the admintools registered and available to a superuser."""
        response = self.get_response(reverse(f"{miz_site.name}:index"), user=self.super_user)
        self.assertTrue("admintools" in response.context_data)
        tools = response.context_data.get("admintools")

        self.assertIn("tools:bulk_ausgabe", tools)
        self.assertEqual(tools["tools:bulk_ausgabe"], "Ausgaben Erstellung")
        self.assertIn("tools:site_search", tools)
        self.assertEqual(tools["tools:site_search"], "Datenbank durchsuchen")
        self.assertIn("tools:dupes_select", tools)
        self.assertEqual(tools["tools:dupes_select"], "Duplikate finden")

    def test_index_tools_mitarbeiter(self):
        """
        Check that staff users only have access to a selected number of index
        tools.
        """
        ct = ContentType.objects.get_for_model(_models.Ausgabe)
        perms = Permission.objects.filter(codename="add_ausgabe", content_type=ct)
        self.staff_user.user_permissions.set(perms)

        response = self.get_response(reverse(f"{miz_site.name}:index"), user=self.staff_user)
        self.assertTrue("admintools" in response.context_data)
        tools = response.context_data.get("admintools").copy()

        self.assertIn("tools:bulk_ausgabe", tools)
        self.assertEqual(tools.pop("tools:bulk_ausgabe"), "Ausgaben Erstellung")
        self.assertIn("tools:site_search", tools)
        self.assertEqual(tools.pop("tools:site_search"), "Datenbank durchsuchen")
        self.assertFalse(tools)

    def test_index_tools_view_only(self):
        """
        Assert that view-only users (i.e. visitors) only see the site_search
        tool.
        """
        visitor_user = User.objects.create_user(username="visitor", password="besucher", is_staff=True)
        ct = ContentType.objects.get_for_model(_models.Ausgabe)
        visitor_user.user_permissions.set([Permission.objects.get(codename="view_ausgabe", content_type=ct)])

        response = self.get_response(reverse(f"{miz_site.name}:index"), user=visitor_user)
        self.assertTrue("admintools" in response.context_data)
        tools = response.context_data.get("admintools").copy()

        self.assertIn("tools:site_search", tools)
        self.assertEqual(tools.pop("tools:site_search"), "Datenbank durchsuchen")
        self.assertFalse(tools)

    def test_changelist_availability_superuser(self):
        """
        Assert that the changelists of all registered ModelAdmins can be
        reached.
        """
        self.client.force_login(self.super_user)
        for model in miz_site._registry:
            opts = model._meta
            with self.subTest(model_name=opts.model_name):
                url = reverse(f"{miz_site.name}:{opts.app_label}_{opts.model_name}_changelist")
                with self.assertNotRaises(Exception):
                    response = self.client.get(url)
                self.assertEqual(response.status_code, 200, msg=url)

    def test_app_index(self):
        """
        Assert that the paths '/admin/dbentry/' and '/admin/' resolve to the
        expected index view functions.
        """
        response = self.client.get("/admin/dbentry/")
        self.assertEqual(response.resolver_match.func.__name__, MIZAdminSite.app_index.__name__)

        response = self.client.get("/admin/")
        self.assertEqual(response.resolver_match.func.__name__, MIZAdminSite.index.__name__)
