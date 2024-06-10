from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models.deletion import Collector
from django.urls import reverse, NoReverseMatch
from django.utils.safestring import mark_safe
from django.views.generic import DeleteView as BaseDeleteView

from dbentry.actions.base import ActionConfirmationView
from dbentry.site.templatetags.mizdb import add_preserved_filters
from dbentry.site.views.base import ModelViewMixin
from dbentry.utils import permission as perms
from dbentry.utils.admin import log_deletion
from dbentry.utils.models import get_deleted_objects
from dbentry.utils.url import urlname


class DeleteView(PermissionRequiredMixin, ModelViewMixin, BaseDeleteView):
    """
    Confirmation for deleting a single model object.

    Accessed from the object's change page.
    """

    title = "Löschen"
    template_name = "mizdb/delete_confirmation.html"

    def get_objects_for_deletion(self):
        return [getattr(self, "object", self.get_object())]

    def get_permission_required(self):
        """Return the delete permission required for this view."""
        return [perms.get_perm("delete", self.opts)]

    def get_success_url(self):
        try:
            return add_preserved_filters(
                {"opts": self.opts, "preserved_filters": self.get_preserved_filters(self.request)},
                reverse(urlname("changelist", self.opts)),
            )
        except NoReverseMatch:
            return reverse("index")

    def form_valid(self, form):
        objects = self.get_objects_for_deletion()

        # Prepare the success message before deleting the objects:
        icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-check"><polyline points="20 6 9 17 4 12"></polyline></svg>"""  # noqa
        objects_str = ", ".join(str(o) for o in objects)
        verbose_name = self.opts.verbose_name_plural if len(objects) > 1 else self.opts.verbose_name
        success_message = f"{icon} {verbose_name} erfolgreich gelöscht: {objects_str}"

        collector = Collector(using="default", origin=objects)
        collector.collect(objects)
        for deleted_objects_set in collector.data.values():
            for obj in deleted_objects_set:
                log_deletion(self.request.user.pk, obj)
        response = super().form_valid(form)

        messages.success(self.request, mark_safe(success_message))
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        deleted_objects, model_count, perms_needed, protected = get_deleted_objects(
            self.request, self.get_objects_for_deletion()
        )
        ctx.update(
            {
                "deleted_objects": deleted_objects,
                "model_count": model_count.items(),
                "perms_needed": perms_needed,
                "protected": protected,
            }
        )
        if protected or perms_needed:
            ctx["title"] = f"Kann {self.opts.verbose_name} nicht löschen"
        else:
            ctx["title"] = "Sind Sie sicher?"
        return ctx


class DeleteSelectedView(DeleteView, ActionConfirmationView):
    """Confirmation for deleting model objects selected on the changelist."""

    action_name = "delete"

    def get_objects_for_deletion(self):
        return self.queryset

    def get_object(self, queryset=None):
        # Hacky, but DeleteView only ever calls self.object.delete(), which
        # also works when self.object is a queryset.
        return self.get_objects_for_deletion()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_changelist_action"] = True
        return ctx

    def post(self, request, *args, **kwargs):
        deleted_objects, model_count, perms_needed, protected = get_deleted_objects(
            self.request, self.get_objects_for_deletion()
        )
        if self.action_confirmed(request) and not protected:
            # User confirmed the deletion. Delete the objects (super) and return
            # None to tell the changelist view that the action was completed.
            super().post(request, *args, **kwargs)
            return None
        else:
            # This POST request was issued from the changelist selection panel.
            # Show the confirmation page.
            return self.get(request, *args, **kwargs)
