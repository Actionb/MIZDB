from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.admin.utils import unquote, NestedObjects
from django.contrib.auth import views as auth_views, get_permission_codename
from django import forms
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import router
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.utils.encoding import force_str
from django.utils.text import capfirst
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
from django.views.generic.base import ContextMixin
from django.views.generic.detail import SingleObjectMixin
from formset.views import FormView, IncompleteSelectResponseMixin, FormViewMixin

from dbentry import models as _models
from .forms import ArtikelForm

from .registry import miz_site, register_edit, register_changelist, ModelType
from dbentry.utils import permission as perms
from dbentry.utils import get_obj_link, log_deletion


class AutocompleteMixin(IncompleteSelectResponseMixin, FormViewMixin):
    pass


class BaseViewMixin(ContextMixin):
    """Mixin for all views of the `miz_site` site."""

    title = ""
    site = miz_site

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_namespace = settings.SITE_NAMESPACE

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'title': self.title,
            'wiki_url': settings.WIKI_URL,
            'model_list': self.site.model_list,
        })
        return ctx


class ModelViewMixin(BaseViewMixin):
    """Mixin for views that interact with a model."""

    model = None
    opts = None
    pk_url_kwarg = "object_id"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.opts = self.model._meta

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'model': self.model,
            'opts': self.model._meta,
        })
        return ctx


class BaseModelView(ModelViewMixin, AutocompleteMixin, UpdateView):

    inlines: list['InlineModel'] = ()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        add = self.extra_context['add']
        title_suffix = 'hinzufügen' if add else 'ändern'
        ctx.update({
            'model': self.model,
            'opts': self.model._meta,
            'add': add,
            'title': f"{capfirst(self.opts.verbose_name)} {title_suffix}"
        })
        return ctx

    def get_object(self, queryset=None):
        if self.extra_context['add'] is False:
            return super().get_object(queryset)

    def get_success_url(self):
        return reverse(
            f"{self.url_namespace}:{self.opts.app_label}_{self.opts.model_name}_changelist"
        )

    def form_valid(self, form):
        # Do not save the form instance until the formsets have been validated.
        self.object = form.save(commit=False)
        formsets = ()
        if all([formset.is_valid() for formset in formsets]):
            # NOTE: Can't we just do this?:
            # form.save()
            self.object.save()
            form.save_m2m()
            for formset in formsets:
                formset.save()
        else:
            # TODO: don't we need to add the formset errors to the context?
            return self.form_invalid(form)

        # Redirect back to the changelist (get_success_url), unless the user
        # wants to add another object or if they want to continue working on
        # the current object.
        success_url = self.get_success_url()
        if extra_data := self.get_extra_data():
            # NOTE: these values are passed in by the submit button
            if extra_data.get('add_another'):
                return JsonResponse({'success_url': self.request.path})
            elif extra_data.get('continue'):
                success_url = reverse(
                    f'{self.url_namespace}:{self.opts.app_label}_{self.opts.model_name}_change',
                    args=[self.object.pk]
                )
                return JsonResponse({'success_url': success_url, 'pk': self.object.pk})
        return JsonResponse({'success_url': success_url})

    ###########################################################################
    #                                   Inlines
    ###########################################################################

    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        for inline_class in self.inlines:
            inline = inline_class(self.model, site)
            if request:
                if not (
                    inline.has_view_or_change_permission(request, obj)
                    or inline.has_add_permission(request, obj)
                    or inline.has_delete_permission(request, obj)
                ):
                    continue
                if not inline.has_add_permission(request, obj):
                    inline.max_num = 0
            inline_instances.append(inline)

        return inline_instances

    def get_formsets_with_inlines(self, request, obj=None):
        """
        Yield formsets and the corresponding inlines.
        """
        for inline in self.get_inline_instances(request, obj):
            yield inline.get_formset(request, obj), inline

    def get_formset_kwargs(self, request, obj, inline, prefix):
        formset_params = {
            "instance": obj,
            "prefix": prefix,
            "queryset": inline.get_queryset(request),
        }
        if request.method == "POST":
            formset_params.update(
                {
                    "data": request.POST.copy(),
                    "files": request.FILES,
                    "save_as_new": "_saveasnew" in request.POST,
                }
            )
        return formset_params

    def _create_formsets(self, request, obj, change):
        """Helper function to generate formsets for add/change_view."""
        formsets = []
        inline_instances = []
        prefixes = {}
        get_formsets_args = [request]
        if change:
            get_formsets_args.append(obj)
        for FormSet, inline in self.get_formsets_with_inlines(*get_formsets_args):
            prefix = FormSet.get_default_prefix()
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
            if prefixes[prefix] != 1 or not prefix:
                prefix = "%s-%s" % (prefix, prefixes[prefix])
            formset_params = self.get_formset_kwargs(request, obj, inline, prefix)
            formset = FormSet(**formset_params)

            def user_deleted_form(request, obj, formset, index):
                """Return whether the user deleted the form."""
                return (
                    inline.has_delete_permission(request, obj)
                    and "{}-{}-DELETE".format(formset.prefix, index) in request.POST
                )

            # Bypass validation of each view-only inline form (since the form's
            # data won't be in request.POST), unless the form was deleted.
            if not inline.has_change_permission(request, obj if change else None):
                for index, form in enumerate(formset.initial_forms):
                    if user_deleted_form(request, obj, formset, index):
                        continue
                    form._errors = {}
                    form.cleaned_data = form.initial
            formsets.append(formset)
            inline_instances.append(inline)
        return formsets, inline_instances


class InlineModel:

    model = None
    verbose_name = None
    verbose_name_plural = None

    form = forms.ModelForm
    formset = forms.BaseInlineFormSet
    extra = 1
    min_num = None
    max_num = None
    fields = None
    exclude = None
    readonly_fields = ()

    def __init__(self, parent_model):
        self.parent_model = parent_model
        self.opts = self.model._meta
    #
    # def get_formset(self, request, obj=None, **kwargs):
    #     """Return a BaseInlineFormSet class for use in add/change views."""
    #     if self.exclude is None and hasattr(self.form, "_meta") and self.form._meta.exclude:
    #         # Use the form's exclude if the inline does not define exclusions.
    #         exclude = list(self.form._meta.exclude)
    #     else:
    #         exclude = list(self.exclude)
    #     exclude.extend(self.readonly_fields)
    #
    #     can_delete = self.has_delete_permission(request, obj)
    #     defaults = {
    #         "form": self.form,
    #         "formset": self.formset,
    #         "fields": self.fields,
    #         "exclude":  exclude or None,
    #         "extra": 1,
    #         "can_delete": can_delete,
    #         **kwargs,
    #     }
    #
    #     base_model_form = defaults["form"]
    #     can_change = self.has_change_permission(request, obj) if request else True
    #     can_add = self.has_add_permission(request, obj) if request else True
    #
    #     # TODO: use javascript to delete relations
    #     class DeleteProtectedModelForm(base_model_form):
    #         def hand_clean_DELETE(self):
    #             """
    #             We don't validate the 'DELETE' field itself because on
    #             templates it's not rendered using the field information, but
    #             just using a generic "deletion_field" of the InlineModelAdmin.
    #             """
    #             if self.cleaned_data.get(DELETION_FIELD_NAME, False):
    #                 using = router.db_for_write(self._meta.model)
    #                 collector = NestedObjects(using=using)
    #                 if self.instance._state.adding:
    #                     return
    #                 collector.collect([self.instance])
    #                 if collector.protected:
    #                     objs = []
    #                     for p in collector.protected:
    #                         objs.append(
    #                             # Translators: Model verbose name and instance
    #                             # representation, suitable to be an item in a
    #                             # list.
    #                             _("%(class_name)s %(instance)s")
    #                             % {"class_name": p._meta.verbose_name, "instance": p}
    #                         )
    #                     params = {
    #                         "class_name": self._meta.model._meta.verbose_name,
    #                         "instance": self.instance,
    #                         "related_objects": get_text_list(objs, _("and")),
    #                     }
    #                     msg = _(
    #                         "Deleting %(class_name)s %(instance)s would require "
    #                         "deleting the following protected related objects: "
    #                         "%(related_objects)s"
    #                     )
    #                     raise ValidationError(
    #                         msg, code="deleting_protected", params=params
    #                     )
    #
    #         def is_valid(self):
    #             result = super().is_valid()
    #             self.hand_clean_DELETE()
    #             return result
    #
    #         def has_changed(self):
    #             # Protect against unauthorized edits.
    #             if not can_change and not self.instance._state.adding:
    #                 return False
    #             if not can_add and self.instance._state.adding:
    #                 return False
    #             return super().has_changed()
    #
    #     defaults["form"] = DeleteProtectedModelForm
    #
    #     if defaults["fields"] is None and not modelform_defines_fields(
    #         defaults["form"]
    #     ):
    #         defaults["fields"] = forms.ALL_FIELDS
    #
    #     return inlineformset_factory(self.parent_model, self.model, **defaults)


class MIZDeleteView(PermissionRequiredMixin, ModelViewMixin, DeleteView):

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
                obj,
                self.request.user,
                site_name=self.url_namespace,
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
            return reverse(f"{self.url_namespace}:index")
        return reverse(
            f"{self.url_namespace}:{self.opts.app_label}_{self.opts.model_name}_changelist"
        )

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


# TODO: check for view/change permission
class MIZHistoryView(BaseViewMixin, SingleObjectMixin, TemplateView):

    title = "Änderungsgeschichte"
    template_name = "mizdb/object_history.html"

    def get_history(self):
        """Get the history of this view's object."""
        return (
            LogEntry.objects.filter(
                object_id=unquote(self.kwargs.get(self.pk_url_kwarg)),
                content_type=get_content_type_for_model(self.model),
            )
            .select_related()
            .order_by("action_time")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['history'] = self.get_history()
        return ctx


class LoginView(FormViewMixin, auth_views.LoginView):
    template_name = "mizdb/registration/login.html"
    success_url = next_page = reverse_lazy("mizdb:index")


class Index(BaseViewMixin, TemplateView):
    title = "Index"
    template_name = "mizdb/index.html"


@register_edit(_models.Artikel)
@register_changelist(_models.Artikel, ModelType.ARCHIVGUT)
class ArtikelView(BaseModelView):
    form_class = ArtikelForm
    model = _models.Artikel
    template_name = "mizdb/base_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        print(f"{ctx=}")
        ctx['title'] = 'Artikel hinzufügen'
        return ctx
