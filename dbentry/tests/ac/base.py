from unittest.mock import patch, Mock

from django.test import tag
from django.urls import reverse
from django.utils.translation import override as translation_override

from dbentry.ac.views import ACBase
from dbentry.tests.base import ViewTestCase
from dbentry.tests.mixins import TestDataMixin, LoggingTestMixin


@tag("dal")
class ACViewTestCase(TestDataMixin, ViewTestCase, LoggingTestMixin):
    path = 'accapture'
    model = None
    create_field = None

    def get_path(self):
        # Needed for the RequestTestCase
        if self.path != 'accapture':
            return super().get_path()
        reverse_kwargs = {'model_name': self.model._meta.model_name}
        if self.model.create_field:
            reverse_kwargs['create_field'] = self.model.create_field
        return reverse(self.path, kwargs=reverse_kwargs)

    @staticmethod
    def get_create_field(model):
        return getattr(model, 'create_field', None)

    def get_view(
            self, request=None, args=None, kwargs=None, model=None,
            create_field=None, forwarded=None, q=''):
        # dbentry.ac.views behave slightly different in their as_view() method
        view = super(ACViewTestCase, self).get_view(request, args, kwargs)
        # The request data will set some of the values - then overwrite/extend
        # them with the passed in arguments.
        if model:
            view.model = model
        elif view.model is None:
            view.model = self.model
        if create_field:
            view.create_field = create_field
        elif view.create_field is None:
            view.create_field = self.get_create_field(view.model)
        if not getattr(view, 'forwarded', None):
            view.forwarded = forwarded or {}
        if not getattr(view, 'q', None):
            view.q = q
        return view


@tag("dal")
class ACViewTestMethodMixin(object):
    view_class = ACBase
    test_data_count = 0
    has_alias = True
    alias_accessor_name = ''

    def test_do_ordering(self):
        # Assert that the ordering of the queryset returned by the view matches
        # the ordering of get_ordering() OR the model.
        view = self.get_view()
        qs_order = list(view.do_ordering(self.queryset).query.order_by)
        self.assertEqual(qs_order, self.model._meta.ordering)
        # Test that do_ordering can deal with get_ordering returning a simple
        # string value instead of a list:
        with patch.object(view, 'get_ordering', new=Mock(return_value="-pk")):
            qs_order = list(view.do_ordering(self.queryset).query.order_by)
            self.assertEqual(qs_order, ["-pk"])
        with patch.object(view, 'get_ordering', new=Mock(return_value=["-pk"])):
            qs_order = list(view.do_ordering(self.queryset).query.order_by)
            self.assertEqual(qs_order, ["-pk"])

    def test_apply_q(self):
        # Test that an object can be found by querying for the data that is was
        # used in its creation.
        if not self.raw_data:
            return
        view = self.get_view()
        for data in self.raw_data:
            for field, value in data.items():
                with self.subTest(field=field, value=value):
                    view.q = str(value)
                    result = view.apply_q(self.queryset)
                    if not result:
                        fail_msg = (
                            f"Could not find test object by querying for field {field!r} "
                            f"with search term {view.q!r}"
                        )
                        self.fail(fail_msg)
                    if isinstance(result, list):
                        if isinstance(result[-1], (list, tuple)):
                            result = (o[0] for o in result)
                        else:
                            result = (o.pk for o in result)
                    else:
                        result = result.values_list('pk', flat=True)
                    self.assertIn(self.obj1.pk, result)

    def test_apply_q_alias(self):
        # Assert that an object can be found through its aliases.
        if not self.has_alias:
            return
        if not self.alias_accessor_name:
            # No point in running this test
            self.warn('Test aborted: no alias accessor name set.')
            return

        # Find an object through its alias
        alias = getattr(self.obj1, self.alias_accessor_name).first()
        if alias is None:
            self.warn('Test aborted: queryset of aliases is empty.')
            return
        view = self.get_view()
        view.q = str(alias)
        result = [obj.pk for obj in view.apply_q(self.queryset)]
        self.assertTrue(
            result,
            msg='View returned no results when querying for alias: ' + view.q
        )
        self.assertIn(self.obj1.pk, result)

    @translation_override(language=None)
    def test_get_create_option(self):
        request = self.get_request()
        view = self.get_view(request)
        create_option = view.get_create_option(context={'object_list': []}, q='Beep')
        if view.has_create_field():
            self.assertEqual(len(create_option), 1)
            self.assertEqual(create_option[0].get('id'), 'Beep')
            self.assertEqual(create_option[0].get('text'), 'Create "Beep"')
            self.assertTrue(create_option[0].get('create_id'))
        else:
            self.assertEqual(len(create_option), 0)

    @tag('logging')
    def test_create_object_no_log_entry(self):
        # no request set on view, no log entry should be created
        view = self.get_view()
        if view.has_create_field():
            obj = view.create_object('Beep')
            with self.assertRaises(AssertionError):
                self.assertLoggedAddition(obj)

    @tag('logging')
    def test_create_object_with_log_entry(self):
        # request set on view, log entry should be created
        # FIXME: this didn't catch that ACCreatable did not create log entries
        request = self.get_request()
        view = self.get_view(request)
        if view.has_create_field():
            obj = view.create_object('Boop')
            self.assertLoggedAddition(obj)

    def test_create_object_strip(self):
        # Assert that the input is stripped for object creation:
        request = self.get_request()
        view = self.get_view(request)
        if view.has_create_field():
            obj = view.create_object('   Boop\n')
            self.assertEqual(getattr(obj, view.create_field), 'Boop')
