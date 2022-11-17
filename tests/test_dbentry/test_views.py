from django import http
from django.core.exceptions import PermissionDenied

from dbentry.views import MIZ_permission_denied_view
from tests.case import ViewTestCase


class TestPermissionDeniedView(ViewTestCase):

    def test_MIZ_permission_denied_view_missing_template(self):
        """
        Calling the view with an unknown template_name should return a
        'Forbidden' response.
        """
        response = MIZ_permission_denied_view(None, None, template_name='beepboop')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(isinstance(response, http.HttpResponseForbidden))

    def test_MIZ_permission_denied_view_response_context(self):
        """
        The response context should contain the exception message and a boolean
        on whether this is a popup.
        """
        exception = PermissionDenied('Exception Text')
        response = MIZ_permission_denied_view(self.get_request(), exception)
        context = response.context_data  # noqa
        self.assertTrue('exception' in context)
        self.assertEqual(context['exception'], 'Exception Text')
        self.assertTrue('is_popup' in context)
