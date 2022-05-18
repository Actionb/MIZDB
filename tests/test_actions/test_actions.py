from unittest import skip

from django.test import TestCase

from dbentry.actions.actions import add_cls_attrs


def dummy_func0():
    pass


def dummy_func1():
    pass
dummy_func1.short_description = 'Beep'  # noqa
dummy_func1.allowed_permissions = 'Boop'


@skip("Has not been reworked yet.")
class TestAddClsAttrsDecorator(TestCase):

    def test_deco_with_cls_attrs_and_no_func_attrs(self):
        dummy_view = type(
            'Dummy', (object, ),
            {'short_description': 'Testdesc', 'allowed_permissions': 'Nope'}
        )
        msg = (
            "Decorator should add attributes to the function from the view "
            "if the attributes are missing from the function."
        )
        decorated_func = add_cls_attrs(dummy_view)(dummy_func0)
        self.assertEqual(decorated_func.short_description, 'Testdesc', msg=msg)
        self.assertEqual(decorated_func.allowed_permissions, 'Nope', msg=msg)

    def test_deco_with_cls_attrs_and_func_attrs(self):
        # Assert that the decorator does not overwrite set attributes.
        dummy_view = type(
            'Dummy', (object, ),
            {'short_description': 'Testdesc', 'allowed_permissions': 'Nope'}
        )
        decorated_func = add_cls_attrs(dummy_view)(dummy_func1)
        self.assertEqual(
            decorated_func.short_description, 'Beep',
            msg="Decorator should not overwrite attributes set on the function."
        )
        self.assertEqual(
            decorated_func.allowed_permissions, 'Boop',
            msg="Decorator should not overwrite attributes set on the function."
        )
