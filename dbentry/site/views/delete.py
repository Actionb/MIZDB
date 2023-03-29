from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import router
from django.urls import reverse
from django.views.generic import DeleteView as BaseDeleteView

from dbentry.site.views.base import ModelViewMixin
from dbentry.utils import permission as perms
from dbentry.utils.admin import log_deletion
from dbentry.utils.html import get_obj_link


class DeleteView(PermissionRequiredMixin, ModelViewMixin, BaseDeleteView):
    title = "Löschen"
    template_name = "mizdb/delete_confirmation.html"

    def get_permission_required(self):
        return [perms.get_perm('delete', self.opts)]

    def get_object(self, queryset=None):
        obj = super().get_object()
        (
            self.deleted_objects,
            self.model_count,
            self.perms_needed,
            self.protected,
        ) = self.get_deleted_objects([obj])
        return obj

    def get_deleted_objects(self, objs):
        using = router.db_for_write(objs[0]._meta.model)
        collector = NestedObjects(using=using, origin=objs)
        collector.collect(objs)
        perms_needed = set()

        def format_callback(obj):
            opts = obj._meta
            if not perms.has_delete_permission(self.request.user, opts):
                perms_needed.add(opts.verbose_name)
            return get_obj_link(
                self.request,
                obj,
                blank=True
            )

        to_delete = collector.nested(format_callback)
        protected = [format_callback(obj) for obj in collector.protected]
        model_count = {
            model._meta.verbose_name_plural: len(objs)
            for model, objs in collector.model_objs.items()
        }
        return to_delete, model_count, perms_needed, protected

    def post(self, request, *args, **kwargs):
        if not self.protected and self.perms_needed:
            raise PermissionDenied
        super().post(request, *args, **kwargs)

    def get_success_url(self):
        if not perms.has_view_permission(self.request.user, self.opts):
            return reverse("index")
        return reverse(url.urlname('changelist', self.opts))

    def form_valid(self, form):
        # NOTE: we're only logging the deletion of the main object.
        #  What about the related objects that will be deleted as well?
        #  Are they all just m2m relations and every other relation
        #  would be protected (like Ausgabe -> Artikel) so it doesn't matter?
        log_deletion(self.request.user.pk, self.object)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'deleted_objects': self.deleted_objects,
            'model_count': self.model_count.items(),
            'perms_needed': self.perms_needed,
            'protected': self.protected,
        })
        return ctx
