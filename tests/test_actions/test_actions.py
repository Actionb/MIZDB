from django.test import TestCase

from dbentry.actions.actions import add_cls_attrs


def func0():
    pass


def func1():
    pass


func1.short_description = 'Foo'  # noqa
func1.allowed_permissions = 'Bar'


class TestAddClsAttrsDecorator(TestCase):
    class View:
        short_description = 'This is a test description.'
        allowed_permissions = ('add_band',)

    view_class = View

    def test_sets_description(self):
        """
        Assert that the decorator assigns the view class' description to the
        view function.
        """
        decorated_func = add_cls_attrs(self.view_class)(func0)
        self.assertEqual(decorated_func.short_description, 'This is a test description.')

    def test_sets_allowed_permissions(self):
        """
        Assert that the decorator assigns the view class' permissions to the
        view function.
        """
        decorated_func = add_cls_attrs(self.view_class)(func0)
        self.assertEqual(decorated_func.allowed_permissions, ('add_band',))

    def test_does_not_override_set_attributes(self):
        """
        Assert that the decorator does not overwrite attributes set on the view
        function.
        """
        decorated_func = add_cls_attrs(self.view_class)(func1)
        self.assertEqual(decorated_func.short_description, 'Foo')
        self.assertEqual(decorated_func.allowed_permissions, 'Bar')
