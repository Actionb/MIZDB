from django import forms
from django.contrib import admin
from django.contrib.admin.helpers import AdminField
from django.contrib.admin.views.main import ORDER_VAR
from django.test import override_settings
from django.urls import path

from dbentry.templatetags.miz_tags import checkbox_label, reset_ordering
from tests.case import AdminTestCase
from tests.models import Artikel

admin_site = admin.AdminSite(name='test')


@admin.register(Artikel, site=admin_site)
class ArtikelAdmin(admin.ModelAdmin):
    list_display = ['schlagzeile', 'seite', 'ausgabe']


class URLConf:
    urlpatterns = [path('test_templatetags/', admin_site.urls)]


@override_settings(ROOT_URLCONF=URLConf)
class TestTags(AdminTestCase):
    admin_site = admin_site
    model = Artikel
    model_admin_class = ArtikelAdmin

    def test_reset_ordering(self):
        """
        Assert that reset_ordering returns a link to the current changelist
        without any query string ordering items.
        """
        request = self.get_request(self.changelist_path + f'?all=&{ORDER_VAR}=1.2')
        self.assertEqual(
            reset_ordering(self.get_changelist(request)),
            f'<span class="small quiet"><a href=?all=>Sortierung zurücksetzen</a></span>'
        )

    def test_reset_ordering_no_ordering(self):
        """
        Assert that reset_ordering returns an empty string if the changelist
        does not have manually-specified ordering.
        """
        request = self.get_request(self.changelist_path + f'?all')
        self.assertFalse(reset_ordering(self.get_changelist(request)))

    def test_checkbox_label(self):
        """
        Assert that checkbox_label returns a label element without the
        vCheckboxLabel class.
        """

        class Form(forms.Form):
            cb = forms.BooleanField(label='Checkbox Test', required=False)

        admin_field = AdminField(Form(), 'cb', is_first=False)
        self.assertEqual(
            checkbox_label(admin_field),
            '<label class="inline" for="id_cb">Checkbox Test:</label>'
        )
