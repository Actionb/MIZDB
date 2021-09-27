from typing import Any, Dict, List, Optional, Sequence, Tuple, Type

from django import forms
from django.contrib import admin
from django.contrib.auth import get_permission_codename
from django.core import checks, exceptions
from django.db import models
from django.db.models import Model, QuerySet
from django.db.models.constants import LOOKUP_SEP
from django.forms import BaseInlineFormSet, ModelForm
from django.http import HttpRequest, HttpResponse
from django.urls import NoReverseMatch, reverse
from django.utils.text import capfirst

from dbentry import models as _models
from dbentry.ac.widgets import make_widget
from dbentry.actions.actions import merge_records
from dbentry.base.forms import MIZAdminInlineFormBase  # type: ignore[attr-defined]
from dbentry.base.models import ComputedNameModel
from dbentry.changelist import MIZChangeList
from dbentry.constants import ATTRS_TEXTAREA
from dbentry.forms import AusgabeMagazinFieldForm
from dbentry.search.admin import MIZAdminSearchFormMixin
from dbentry.utils import get_fields_and_lookups, get_model_relations
from dbentry.utils.admin import construct_change_message

FieldsetList = List[Tuple[Optional[str], dict]]


# TODO: enable delete_related on inlines:
# RelatedFieldWidgetWrapper disables can_delete_related for inlines because of
# cascading:
#        # XXX: The deletion UX can be confusing when dealing with cascading deletion.
#        cascade = getattr(rel, 'on_delete', None) is CASCADE
#        self.can_delete_related = not multiple and not cascade and can_delete_related


class MIZModelAdmin(MIZAdminSearchFormMixin, admin.ModelAdmin):
    """
    Base ModelAdmin for this app.

    Attributes:
        - ``crosslink_labels`` (dict): mapping of related_model_name: label
          used to give crosslinks custom labels.
        - ``collapse_all`` (bool): context variable used in the inline templates.
          If True, all inlines start out collapsed unless they contain data.
        - ``superuser_only`` (bool): if true, only a superuser can interact
          with this ModelAdmin.
        - ``index_category`` (str): the name of the 'category' this ModelAdmin
          should be listed under. A fake app is created for each category to
          group them on the index page.
    """

    crosslink_labels: dict
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
        if not hasattr(self, 'crosslink_labels') or self.crosslink_labels is None:
            self.crosslink_labels = {}

    def check(self, **kwargs: Any) -> list:
        errors = super().check(**kwargs)
        errors.extend(self._check_fieldset_fields(**kwargs))
        errors.extend(self._check_search_fields_lookups(**kwargs))
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
                        checks.Error(
                            "fieldset '%s' contains invalid item: '%s'. %s" % (
                                fieldset_name, field, e.args[0]),
                            obj=self.__class__
                        )
                    )
        return errors

    def _check_search_fields_lookups(self, **_kwargs: Any) -> List[checks.CheckMessage]:
        """Check that all search fields and their lookups are valid."""
        errors = []
        msg_template = "Invalid search field '%s': %s"
        for search_field in self.get_search_fields(request=None):
            if search_field[0] in ('=', '^', '@'):
                # Lookup shortcut prefixes for ModelAdmin.construct_search.
                search_field = search_field[1:]
            try:
                get_fields_and_lookups(self.model, search_field)
            except (exceptions.FieldDoesNotExist, exceptions.FieldError) as e:
                errors.append(
                    checks.Error(
                        msg_template % (search_field, e.args[0]),
                        obj=self.__class__
                    )
                )
        return errors

    def formfield_for_foreignkey(
            self,
            db_field: models.Field,
            request: HttpRequest,
            **kwargs: Any
    ) -> forms.Field:
        if 'widget' not in kwargs:
            kwargs['widget'] = make_widget(model=db_field.related_model)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> Type[MIZChangeList]:
        return MIZChangeList

    def get_index_category(self) -> str:
        """Return the index category of this ModelAdmin.

        Called by MIZAdminSite to create 'fake' apps for grouping purposes.
        """
        return self.index_category

    def has_merge_permission(self, request: HttpRequest) -> bool:
        """Check that the user has permission to merge records."""
        codename = get_permission_codename('merge', self.opts)
        # noinspection PyUnresolvedReferences
        return request.user.has_perm(
            '{}.{}'.format(self.opts.app_label, codename)
        )

    # noinspection PyMethodMayBeStatic
    def has_alter_bestand_permission(self, request: HttpRequest) -> bool:
        """Check that the user has permission to change inventory quantities."""
        # noinspection PyUnresolvedReferences,PyProtectedMember
        opts = _models.Bestand._meta
        perms = [
            "%s.%s" % (opts.app_label, get_permission_codename(action, opts))
            for action in ('add', 'change', 'delete')
        ]
        # noinspection PyUnresolvedReferences
        return request.user.has_perms(perms)

    def get_exclude(self, request: HttpRequest, obj: Optional[Model] = None) -> list:
        """Exclude all concrete M2M fields as those are handled by inlines."""
        self.exclude = super().get_exclude(request, obj)
        if self.exclude is None:
            self.exclude = []
            # FIXME: isn't this for loop over-indented? Shouldn't this exclude
            #  m2m fields even if 'exclude' was defined?
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
        if not default_fieldset:
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

    def _add_pk_search_field(self, search_fields: Sequence) -> list:
        """
        Add a search field for the primary key to search_fields if missing.

        Unless the ModelAdmin instance has a search form (which is presumed to
        take over the duty of filtering for primary keys), 'pk__iexact' is added
        to the given list 'search_fields'.
        If the primary key is a OneToOneRelation, 'pk__pk__iexact' is added
        instead.

        Returns a copy of the passed in search_fields list.
        """
        search_fields = list(search_fields)
        if self.has_search_form():
            # This ModelAdmin instance has a search form. Assume that the form
            # contains a field to search for primary keys; no need to add
            # another primary key search field.
            return search_fields
        # noinspection PyProtectedMember
        pk_field = self.model._meta.pk
        for search_field in search_fields:
            if LOOKUP_SEP in search_field:
                field, _ = search_field.split(LOOKUP_SEP, 1)
            else:
                field = search_field
            if not field[0].isalpha() and field[0] != '_':
                # Lookup alias prefixes for ModelAdmin.construct_search:
                # '=', '^', '@' etc.
                field = field[1:]
            if field in ('pk', pk_field.name):
                # Done here, search_fields already contains a custom
                # primary key search field.
                break
        else:
            search_fields.append(
                'pk__pk__iexact' if pk_field.is_relation else 'pk__iexact'
            )
        return search_fields

    def get_search_fields(self, request=None):
        if self.search_fields:
            search_fields = list(self.search_fields)
        else:
            search_fields = list(self.model.get_search_fields())
        return self._add_pk_search_field(search_fields)

    def add_crosslinks(self, object_id: str, labels: Optional[dict] = None) -> Dict[str, list]:
        """
        Provide the template with data to create links to related objects.

        Crosslinks are links on an instance's change form that send the user
        to the changelist containing the instance's related objects.
        """
        new_extra: dict = {'crosslinks': []}
        if labels is None:
            labels = {}

        inline_models = {i.model for i in self.inlines}
        # Walk through all reverse relations and collect the model and
        # model field to query against as well as the assigned name for the
        # relation -- unless an inline is covering that reverse relation.
        relations = []
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
                # a crosslink that leads back to *this* model's changelist
                # (unless it's a self relation).
                query_model = rel.model
                query_field = rel.name
            if rel.related_model == _models.BaseBrochure:
                # Handle a special case of model inheritance.
                # Add crosslinks to the children of BaseBrochure rather than
                # to BaseBrochure itself as it does not have a changelist:
                # reversing for an url would fail.
                # FIXME: Ugly code! MIZModelAdmin shouldn't have to know BaseBrochure!
                relations.extend(
                    [
                        (_models.Brochure, rel.remote_field.name, None),
                        (_models.Kalender, rel.remote_field.name, None),
                        (_models.Katalog, rel.remote_field.name, None)
                    ]
                )
            else:
                relations.append((query_model, query_field, rel.related_name))

        # Create the context data for the crosslinks.
        for query_model, query_field, related_name in relations:
            # noinspection PyProtectedMember
            opts = query_model._meta
            try:
                url = reverse(
                    "admin:{}_{}_changelist".format(opts.app_label, opts.model_name)
                )
            except NoReverseMatch:
                # NoReverseMatch, no link that leads anywhere!
                continue

            count = query_model.objects.filter(**{query_field: object_id}).count()
            if not count:
                # No point showing an empty changelist.
                continue
            # Add the query string to the url:
            url += f"?{query_field}={object_id}"

            # Prepare the label for the link with the following priorities:
            #   - a passed in label
            #   - an explicitly declared related_name
            #       (unless the relation was automatically created,
            #       the default for related_name is None)
            #    - the verbose_name_plural of the related_model
            if opts.model_name in labels:
                label = labels[opts.model_name]
            elif related_name:
                # Automatically created related_names won't look pretty!
                label = " ".join(
                    capfirst(s)
                        for s in related_name.replace('_', ' ').split()
                )
            else:
                label = opts.verbose_name_plural

            label = "{label} ({count})".format(
                label=label, count=str(count)
            )
            new_extra['crosslinks'].append({'url': url, 'label': label})
        return new_extra

    # noinspection PyUnusedLocal
    def add_extra_context(
            self,
            request: Optional[HttpRequest] = None,
            extra_context: Optional[dict] = None,
            object_id: Optional[str] = None
    ) -> dict:
        """Add crosslinks as extra context."""
        new_extra = extra_context or {}
        if object_id:
            new_extra.update(self.add_crosslinks(object_id, self.crosslink_labels))
        new_extra['collapse_all'] = self.collapse_all
        return new_extra

    def add_view(
            self,
            request: HttpRequest,
            form_url: str = '',
            extra_context: dict = None
    ) -> HttpResponse:
        """View for adding a new object."""
        new_extra = self.add_extra_context(
            request=request, extra_context=extra_context
        )
        return super().add_view(request, form_url, new_extra)

    def change_view(
            self,
            request: HttpRequest,
            object_id: Optional[str],
            form_url: str = '',
            extra_context: dict = None
    ) -> HttpResponse:
        """View for changing an object."""
        new_extra = self.add_extra_context(
            request=request, extra_context=extra_context,
            object_id=object_id
        )
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
        else:
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

    def get_result_list_annotations(self) -> dict:
        """
        Return annotations that are expected by list_display items.

        These annotations will be added to the 'result_list' queryset in
        changelist.get_results() *after* the counts for the paginator and the
        full count have been queried. This way these annotations aren't
        included in the count queries, which would slow them down.

        Don't use this to add annotations that are required for the query to
        return the correct results/count.
        """
        return {}

    def response_action(self, request: HttpRequest, queryset: QuerySet):
        # Actions are called with the queryset returned by the changelist's
        # get_queryset() method. Any additional annotations provided by
        # get_result_list_annotations will not be included as these are added
        # by changelist.get_results().
        # If an annotation is part of the queryset ordering, but the annotation
        # was not added to the queryset, an iteration over the queryset will
        # fail. To avoid this from occurring, add the annotations to the
        # action's queryset.
        queryset = queryset.annotate(**self.get_result_list_annotations() or {})
        return super().response_action(request, queryset)


class BaseInlineMixin(object):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.verbose_model:
            # noinspection PyUnresolvedReferences,PyProtectedMember
            verbose_opts = self.verbose_model._meta
            self.verbose_name = verbose_opts.verbose_name
            self.verbose_name_plural = verbose_opts.verbose_name_plural

    def formfield_for_foreignkey(
            self,
            db_field: models.Field,
            request: HttpRequest,
            **kwargs: Any
    ) -> forms.Field:
        if 'widget' not in kwargs:
            kwargs['widget'] = make_widget(model=db_field.related_model)
        # noinspection PyUnresolvedReferences
        return super().formfield_for_foreignkey(db_field, request, **kwargs)  # type: ignore[misc]


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
