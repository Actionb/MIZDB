from unittest.mock import patch
from urllib.parse import urlencode

from dbentry.site.forms import FeedbackForm
from dbentry.site.views.feedback import FeedbackView
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from tests.case import ViewTestCase

REQUIRED_EMAIL_SETTINGS = {
    "ADMINS": [("Alice", "alice@admin.com")],
    "EMAIL_HOST": "smtp.test.de",
    "EMAIL_HOST_USER": "feedback@mizdb.de",
    "EMAIL_HOST_PASSWORD": "foo",
}


@override_settings(**REQUIRED_EMAIL_SETTINGS)
class TestFeedbackView(ViewTestCase):
    view_class = FeedbackView

    def setUp(self):
        self.form = FeedbackForm(data={"subject": "Testing", "message": "This is a test for sending feedback mail."})
        self.form.is_valid()

    def test_form_valid(self):
        """
        Assert that form_valid sends the email and redirects back to the index
        page with a user message.
        """
        request = self.get_response("/").wsgi_request  # enable messages
        view = self.get_view(request=request)

        response = view.form_valid(self.form)
        self.assertEqual(len(getattr(mail, "outbox")), 1)  # mail.outbox only exists during tests
        self.assertMessageSent(request, "Feedback erfolgreich versendet!")
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, reverse("index"))

    def test_form_valid_send_failed(self):
        """
        Assert that form_valid redirects back to the feedback page with a user
        message if sending the feedback failed.
        """
        request = self.get_response("/").wsgi_request  # enable messages
        view = self.get_view(request=request)

        with patch("dbentry.site.views.feedback.mail_admins", side_effect=Exception):
            response = view.form_valid(self.form)
            self.assertEqual(len(getattr(mail, "outbox")), 0)  # mail.outbox only exists during tests
        self.assertMessageSent(request, "Beim Versenden ist etwas schief gelaufen.")
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, f"{reverse('feedback')}?{urlencode(self.form.cleaned_data)}")

    def test_create_mail_message(self):
        """Assert that _create_mail_message returns the expected message."""
        self.assertEqual(
            self.view_class._create_mail_message(self.super_user, {"message": "foo"}),
            f"Benutzer {self.super_user.username} hat Feedback eingereicht:\n{'-' * 80}\nfoo",
        )

    def test_create_mail_message_email(self):
        """
        Asser that _create_mail_message returns a message with an email attached
        if the form data 'email' is set.
        """
        expected_message = (
            f"Benutzer {self.super_user.username} (foo@bar.com) hat Feedback eingereicht:\n{'-' * 80}\nfoo"
        )
        self.assertEqual(
            self.view_class._create_mail_message(self.super_user, data={"message": "foo", "email": "foo@bar.com"}),
            expected_message,
        )
