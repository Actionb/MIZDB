from urllib import parse
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import mail_admins
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.views.generic import FormView

from dbentry.site.forms import FeedbackForm
from dbentry.site.views.base import BaseViewMixin, ONLINE_HELP_INDEX


class FeedbackView(BaseViewMixin, LoginRequiredMixin, FormView):
    template_name = "mizdb/feedback.html"
    form_class = FeedbackForm
    success_url = reverse_lazy("index")
    title = "Feedback senden"
    help_url = parse.urljoin(ONLINE_HELP_INDEX, "email.html")
    offline_help_url = reverse_lazy("help", kwargs={"page_name": "email"})

    @staticmethod
    def _create_mail_message(user, data):
        if email := data.get("email", ""):
            email = f" ({email})"
        return f"Benutzer {user.username}{email} hat Feedback eingereicht:\n{'-'*80}\n{data['message']}"

    def get_initial(self):
        return {
            "subject": self.request.GET.get("subject"),
            "message": self.request.GET.get("message"),
            "email": self.request.GET.get("email"),
        }

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            mail_admins(
                subject=f"[FEEDBACK] {data['subject']}",
                message=self._create_mail_message(self.request.user, data),
                fail_silently=False,
            )
        except Exception:
            messages.error(self.request, message="Beim Versenden ist etwas schief gelaufen.")
            return HttpResponseRedirect(f"{reverse('feedback')}?{urlencode(data)}")
        messages.success(self.request, message="Feedback erfolgreich versendet!")
        return super().form_valid(form)
