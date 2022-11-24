from typing import Any, List, Optional, Tuple, Type

from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.admin.views.main import ORDER_VAR
from django.contrib.auth import get_permission_codename
from django.core import checks, exceptions
from django.db import models
from django.db.models import Model, QuerySet
from django.forms import BaseInlineFormSet, ChoiceField, ModelForm
from django.http import HttpRequest, HttpResponse
from django.urls import NoReverseMatch, reverse
from django.utils.text import capfirst

from dbentry import models as _models
from dbentry.ac.widgets import make_widget
from dbentry.actions.actions import merge_records
from dbentry.base.forms import ATTRS_TEXTAREA, MIZAdminInlineFormBase
from dbentry.base.models import ComputedNameModel
from dbentry.changelist import MIZChangeList
from dbentry.forms import AusgabeMagazinFieldForm
from dbentry.query import MIZQuerySet
from dbentry.search.admin import MIZAdminSearchFormMixin
from dbentry.utils import get_fields_and_lookups, get_model_relations
from dbentry.utils.admin import construct_change_message

FieldsetList = List[Tuple[Optional[str], dict]]
BESTAND_MODEL_NAME = 'dbentry.Bestand'


class AutocompleteMixin(object):
    """
    A mixin for model admin and admin inlines that creates autocomplete widgets
    for ForeignKey fields.

    Attributes:
        - ``tabular_autocomplete`` (list): list of field names for which
          tabular autocomplete widgets should be used
    """
    tabular_autocomplete: list = []

    def formfield_for_foreignkey(
            self,
            db_field: models.Field,
            request: HttpRequest,
            **kwargs: Any
    ) -> ChoiceField:
        if 'widget' not in kwargs:
            kwargs['widget'] = make_widget(
                model=db_field.related_model,
                tabular=db_field.name in self.tabular_autocomplete
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)  # type: ignore[misc]


class MIZModelAdmin(AutocompleteMixin, MIZAdminSearchFormMixin, admin.ModelAdmin):
    """
    Base ModelAdmin for this app.

    Attributes:
        - ``changelist_link_labels`` (dict): mapping of related_model_name: label
          to give changelist_links custom labels
        - ``collapse_all`` (bool): context variable used in the inline templates.
          If True, all inlines start out collapsed unless they contain data.
        - ``superuser_only`` (bool): if true, only a superuser can interact
          with this ModelAdmin.
        - ``index_category`` (str): the name of the 'category' this ModelAdmin
          should be listed under. A fake app is created for each category to
          group them on the index page.
    """

    changelist_link_labels: dict
    collapse_all: bool = False
    superuser_only: bool = False
    index_category: str = 'Sonstige'

    # Add the merge_records action to all MIZModelAdmin classes.
    # Using miz_site.add_action to add that action to all model admin instances
    # would also add merge_records to Group/UserAdmin, which is neither
    # desired nor functional (they'd need a has_merge_permission func).
    actions = [merge_records]

    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs=ATTRS_TEXTAREA)},
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'changelist_link_labels') or self.changelist_link_labels is None:
            self.changelist_link_labels = {}

    def check(self, **kwargs: Any) -> list:
        errors = super().check(**kwargs)
        errors.extend(self._check_fieldset_fields(**kwargs))
        return errors

    def _check_fieldset_fields(self, **_kwargs: Any) -> List[checks.CheckMessage]:
        """Check for unknown field names in the fieldsets attribute."""
        if not self.fieldsets:
            return []
        errors = []
        for fieldset in self.fieldsets:
            fieldset_name, options = fieldset
            if 'fields' not in options:
                continue
            for field in options['fields']:
                try:
                    if isinstance(field, (list, tuple)):
                        for _field in field:
                            get_fields_and_lookups(self.model, _field)
                    else:
                        get_fields_and_lookups(self.model, field)
                except (exceptions.FieldDoesNotExist, exceptions.FieldError) as e:
                    errors.append(
                        # TODO: use f-strings
                        checks.Error(
                            "fieldset '%s' contains invalid item: '%s'. %s" % (
                                fieldset_name, field, e.args[0]),
                            obj=self.__class__
                        )
                    )
        return errors

    # noinspection PyMethodMayBeStatic
    def has_superuser_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        annotations = self.get_changelist_annotations()
        if annotations:
            return qs.annotate(**annotations)
        return qs

    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> Type[MIZChangeList]:
        return MIZChangeList

    def get_index_category(self) -> str:
        """
        Return the index category of this ModelAdmin.

        Called by MIZAdminSite to create 'fake' apps for grouping purposes.
        """
        return self.index_category

    def has_merge_permission(self, request: HttpRequest) -> bool:
        """Check that the user has permission to merge records."""
        # This method is called by ModelAdmin._filter_actions_by_permissions.
        codename = get_permission_codename('merge', self.opts)
        # noinspection PyUnresolvedReferences
        return request.user.has_perm(
            '{}.{}'.format(self.opts.app_label, codename)
        )

    # noinspection PyMethodMayBeStatic
    def has_alter_bestand_permission(self, request: HttpRequest) -> bool:
        """Check that the user has permission to change inventory quantities."""
        # This method is called by ModelAdmin._filter_actions_by_permissions.
        opts = apps.get_model(BESTAND_MODEL_NAME)._meta
        perms = [
            "%s.%s" % (opts.app_label, get_permission_codename(action, opts))
            for action in ('add', 'change', 'delete')
        ]
        # noinspection PyUnresolvedReferences
        return request.user.has_perms(perms)

    def get_exclude(self, request: HttpRequest, obj: Optional[Model] = None) -> list:
        # Unless the ModelAdmin specifies 'exclude', exclude M2M fields
        # declared on this model. It is expected that those relations will be
        # handled by inlines.
        self.exclude = super().get_exclude(request, obj)
        if self.exclude is None:
            self.exclude = []
            for fld in self.opts.get_fields():
                if fld.concrete and fld.many_to_many:
                    self.exclude.append(fld.name)
        return self.exclude

    # noinspection PyMethodMayBeStatic
    def _add_bb_fieldset(self, fieldsets: FieldsetList) -> FieldsetList:
        """
        Append a fieldset for 'Beschreibung & Bemerkungen'.

        If any of these two fields are part of the default fieldset,
        move them out of there to their own fieldset.
        """
        default_fieldset = dict(fieldsets).get(None, None)
        if not default_fieldset:  # pragma: no cover
            return fieldsets
        # default_fieldset['fields'] might be a direct reference to
        # self.get_fields(): make a copy to leave the original list untouched.
        fields = default_fieldset['fields'].copy()
        bb_fields = []
        if 'beschreibung' in fields:
            bb_fields.append(fields.pop(fields.index('beschreibung')))
        if 'bemerkungen' in fields:
            bb_fields.append(fields.pop(fields.index('bemerkungen')))
        if bb_fields:
            fieldsets.append(
                (
                    'Beschreibung & Bemerkungen', {
                        'fields': bb_fields,
                        'classes': ['collapse', 'collapsed']
                    }
                )
            )
        default_fieldset['fields'] = fields
        return fieldsets

    def get_fieldsets(self, request: HttpRequest, obj: Optional[Model] = None) -> FieldsetList:
        fieldsets = super().get_fieldsets(request, obj)
        return self._add_bb_fieldset(fieldsets)

    # noinspection PyMethodMayBeStatic
    def _get_changelist_link_relations(self) -> Optional[List[Tuple]]:
        """
        Hook to specify relations to follow with the changelist_links.
        
        A list of 3-tuples should be returned. The tuples must consist of:
          - model class: the related model to query for the related objects
          - field name: the name of the field of the related model to query
            against
          - label: the label for the link, optional
            
        If the return value is None, add_changelist_links will try to add links
        for all reverse relations of this model.
        """
        return None

    def add_changelist_links(self, object_id: str = '', labels: Optional[dict] = None) -> list:
        """
        Provide context data for the given object's change form template that 
        includes links to the changelists of related objects.

        Returns a list of dictionaries:
            [{'url': <changelist url>, 'label': <label for the link>}, ...]
        """
        if not object_id:
            return []

        links = []
        if labels is None:  # pragma: no cover
            labels = {}

        relations = self._get_changelist_link_relations()
        if relations is None:
            # Walk through all reverse relations and collect the model and
            # model field to query against as well as the assigned name for the
            # relation -- unless an admin inline is covering that relation.
            relations = []
            inline_models = {i.model for i in self.inlines}
            for rel in get_model_relations(self.model, forward=False, reverse=True):
                if rel.many_to_many:
                    inline_model = rel.through
                else:
                    inline_model = rel.related_model
                if inline_model in inline_models:
                    continue

                query_model = rel.related_model
                query_field = rel.remote_field.name
                if rel.many_to_many and query_model == self.model:
                    # M2M relations are symmetric, but we wouldn't want to create
                    # a changelist_link that leads back to *this* model's 
                    # changelist (unless it's a self relation).
                    query_model = rel.model
                    query_field = rel.name
                # Use a 'prettier' related_name as the default for the label.
                if rel.related_name:
                    label = " ".join(capfirst(s) for s in rel.related_name.split('_'))
                else:
                    label = None
                relations.append((query_model, query_field, label))

        # Create the context data for the changelist_links.
        for query_model, query_field, label in relations:
            opts = query_model._meta
            try:
                url = reverse("admin:{}_{}_changelist".format(opts.app_label, opts.model_name))
            except NoReverseMatch:
                # NoReverseMatch, no link that leads anywhere!
                continue

            count = query_model.objects.filter(**{query_field: object_id}).count()
            if not count:  # pragma: no cover
                # No point showing an empty changelist.
                continue
            # Add the query string to the url:
            url += f"?{query_field}={object_id}"

            # Prepare the label for the link.
            if opts.model_name in labels:
                label = labels[opts.model_name]
            else:
                label = label or opts.verbose_name_plural

            links.append({'url': url, 'label': f"{label} ({count!s})"})
        return links

    def add_extra_context(self, object_id: str = '', **extra_context: Any) -> dict:
        """Add extra context specific to this ModelAdmin."""
        extra_context.update(
            {
                'collapse_all': self.collapse_all,
                'changelist_links': self.add_changelist_links(
                    object_id, self.changelist_link_labels
                )
            }
        )
        return extra_context

    def add_view(
            self,
            request: HttpRequest,
            form_url: str = '',
            extra_context: Optional[dict] = None
    ) -> HttpResponse:
        """View for adding a new object."""
        return super().add_view(request, form_url, self.add_extra_context(**(extra_context or {})))

    def change_view(
            self,
            request: HttpRequest,
            object_id: str = '',
            form_url: str = '',
            extra_context: Optional[dict] = None
    ) -> HttpResponse:
        """View for changing an object."""
        new_extra = self.add_extra_context(object_id=object_id, **(extra_context or {}))
        return super().change_view(request, object_id, form_url, new_extra)

    def construct_change_message(
            self,
            request: HttpRequest,
            form: ModelForm,
            formsets: List[BaseInlineFormSet],
            add: bool = False
    ) -> List[dict]:
        """
        Construct a JSON structure describing changes from a changed object.
        """
        return construct_change_message(form, formsets, add)

    def has_module_permission(self, request: HttpRequest) -> bool:
        if self.superuser_only:
            # Hide the associated models from the index if
            # the current user is not a superuser
            # noinspection PyUnresolvedReferences
            return request.user.is_superuser
        return super().has_module_permission(request)

    def save_model(self, request: HttpRequest, obj: Model, form: ModelForm, change: bool) -> None:
        if isinstance(obj, ComputedNameModel):
            # Delay the update of the _name until ModelAdmin._changeform_view
            # has saved the related objects via save_related. This is to avoid
            # update_name building a name with outdated related objects.
            obj.save(update=False)
        else:  # pragma: no cover
            super().save_model(request, obj, form, change)

    def save_related(
            self,
            request: HttpRequest,
            form: ModelForm,
            formsets: List[BaseInlineFormSet],
            change: bool
    ) -> None:
        super().save_related(request, form, formsets, change)
        if isinstance(form.instance, ComputedNameModel):
            # Update the instance's _name now. save_model was called earlier.
            form.instance.update_name(force_update=True)

    def get_changelist_annotations(self) -> dict:
        """Return annotations necessary for the changelist queryset."""
        return {}

    def get_search_results(
            self,
            request: HttpRequest,
            queryset: MIZQuerySet,
            search_term: str
    ) -> tuple[MIZQuerySet, bool]:
        if not search_term:
            return queryset, False
        # Do a full text search. Respect ordering specified on the changelist.
        return queryset.search(search_term, ranked=ORDER_VAR not in request.GET), False


class BaseInlineMixin(AutocompleteMixin):
    """
    A mixin for inline classes.

    It overrides the formfields for ForeignKeys, adds an optional ``description``
    and simplifies the assignment of verbose_name and verbose_name_plural.
    Sets extra for formsets to 1.

    Attributes:
        - ``verbose_model`` (model class): the model whose verbose_name and
          verbose_name_plural attributes will be used to override this
          inline's default ones.
        - ``description`` (str): short description of this inline in relation
          to its parent ModelAdmin.
    """

    verbose_model: Type[Model] = None  # type: ignore[assignment]
    extra: int = 1
    classes: list = ['collapse']
    description: str = ''
    form: ModelForm = MIZAdminInlineFormBase

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.verbose_model:
            # noinspection PyUnresolvedReferences
            verbose_opts = self.verbose_model._meta
            self.verbose_name = verbose_opts.verbose_name
            self.verbose_name_plural = verbose_opts.verbose_name_plural


class BaseTabularInline(BaseInlineMixin, admin.TabularInline):
    pass


class BaseStackedInline(BaseInlineMixin, admin.StackedInline):
    pass


class BaseAliasInline(BaseTabularInline):
    verbose_name_plural = 'Alias'


class BaseGenreInline(BaseTabularInline):
    verbose_model = _models.Genre


class BaseSchlagwortInline(BaseTabularInline):
    verbose_model = _models.Schlagwort


class BaseAusgabeInline(BaseTabularInline):
    form = AusgabeMagazinFieldForm
    verbose_model = _models.Ausgabe
    fields = ['ausgabe__magazin', 'ausgabe']


class BaseOrtInLine(BaseTabularInline):
    verbose_name = 'Ort'
    verbose_name_plural = 'Assoziierte Orte'
