"""Tests for the registry handling the dbentry site views."""

from django.test import TestCase
from django.views import View

from dbentry.site.registry import ModelType, Registry, register_changelist, register_edit

from .models import Foo

test_site = Registry()


@register_edit(Foo, site=test_site)
class EditView(View):
    pass


@register_changelist(Foo, category=ModelType.ARCHIVGUT, site=test_site)
class ChangelistView(View):
    pass


class TestRegistry(TestCase):
    def test_views(self):
        self.assertEqual(test_site.views, {Foo: EditView})

    def test_changelists(self):
        self.assertEqual(test_site.changelists, {Foo: ChangelistView})

    def test_categories(self):
        expected = [
            (ModelType.ARCHIVGUT.value, [Foo._meta]),
            (ModelType.STAMMDATEN.value, []),
            (ModelType.SONSTIGE.value, []),
        ]
        self.assertEqual(list(test_site.model_list), expected)

    def test_register_edit(self):
        for model_arg in (Foo, [Foo]):
            site = Registry()
            with self.subTest(model_arg=model_arg):
                register_edit(model_arg, site=site)(EditView)
                self.assertIn(Foo, site.views)

    def test_register_changelist(self):
        for model_arg in (Foo, [Foo]):
            site = Registry()
            with self.subTest(model_arg=model_arg):
                register_changelist(model_arg, site=site)(ChangelistView)
                self.assertIn(Foo, site.changelists)

    def test_register_changelist_invalid_category(self):
        site = Registry()
        with self.assertRaises(ValueError):
            register_changelist(Foo, category="foobar", site=site)
