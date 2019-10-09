from django import forms
from django.core import checks, exceptions
from django.contrib import admin
from django.contrib.auth import get_permission_codename
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.urls import reverse, NoReverseMatch
from django.utils.translation import override as translation_override
from django.utils.encoding import force_text
from django.utils.text import capfirst

from DBentry import models as _models
from DBentry.ac.widgets import make_widget
from DBentry.actions import merge_records
from DBentry.base.models import ComputedNameModel
from DBentry.changelist import MIZChangeList
from DBentry.constants import ATTRS_TEXTAREA
from DBentry.forms import AusgabeMagazinFieldForm
from DBentry.helper import MIZAdminFormWrapper
from DBentry.search.admin import MIZAdminSearchFormMixin
from DBentry.utils import (
    get_model_relations, ensure_jquery, get_fields_and_lookups,
    resolve_list_display_item
)


class MIZModelAdmin(MIZAdminSearchFormMixin, admin.ModelAdmin):
    """
    Base ModelAdmin for this app.

    Attributes:
        googlebtns (list): a list of formfield names that get a button that
            opens a google search page with the field's value.
            (Used on BandAdmin and MusikerAdmin)
        crosslink_labels (dict): mapping of related_model_name: custom_label
            used to give crosslinks custom labels.
        collapse_all (bool): context variable used in the inline templates.
            If True, all inlines start out collapsed unless they contain data.
        superuser_only (bool): if true, only a superuser can interact with
            this ModelAdmin.
        index_category (str): the name of the 'category' this ModelAdmin should
            be listed under. A fake app is created for each category to group
            them on the index page.
    """

    # FIXME: self.get_search_fields access self.search_fields which is not declared
    # TODO: googlebtns: fields in this list should be wrapped into a custom widget
    # (let the widget render the button instead of the fieldset template)
    googlebtns = []
    crosslink_labels = {}
    collapse_all = False
    superuser_only = False
    index_category = 'Sonstige'

    actions = [merge_records]

    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs=ATTRS_TEXTAREA)},
    }
    # TODO: let the MIZ changelist template extend the default one
    # change_list_template = 'miz_changelist.html'

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_search_fields_lookups(**kwargs))
        errors.extend(self._check_list_item_annotations(**kwargs))
        return errors

    def _check_search_fields_lookups(self, **kwargs):
        """Check that all search fields and their lookups are valid."""
        errors = []
        for search_field in self.get_search_fields(request=None):
            if not search_field[0].isalpha() and search_field[0] != '_':
                # Lookup alias prefixes for ModelAdmin.construct_search:
                # '=', '^', '@' etc.
                search_field = search_field[1:]
            try:
                get_fields_and_lookups(self.model, search_field)
            except exceptions.FieldDoesNotExist as e:
                errors.append(checks.Critical(e.args[0]))
            except exceptions.FieldError as e:
                errors.append(checks.Critical(e.args[0]))
        return errors

    def _check_list_item_annotations(self, **kwargs):
        """Check items in 'list_display' that are expected to be sortable."""
        errors = []
        for list_item in self.list_display:
            func = resolve_list_display_item(self, list_item)
            if func is None or not getattr(func, 'admin_order_field', None):
                # Either resolve_list_display_item could not resolve the item
                # at all (returned None) or func is something without an
                # 'admin_order_field' attribute.
                # In either case, this list_item is not sortable.
                continue
            annotation = getattr(func, 'annotation', None)
            if not annotation:
                # When the checks are run, we cannot check if the queryset needs
                # an annotation for this order field (it might already have one).
                # _annotate_for_list_display only adds annotations if both
                # 'admin_order_field' and 'annotation' are declared.
                continue
            elif not isinstance(annotation, models.Aggregate):
                errors.append(checks.Critical(
                    "%(model_admin)s.%(func)s.annotation "
                    "is not an aggregate: %(annotation)s" % {
                        'model_admin': self.__class__.__name__,
                        'func': func.__name__,
                        'annotation': type(annotation)
                    }
                ))
        return errors

    def _annotate_for_list_display(self, request, queryset):
        """
        Add annotations for callable, sortable list display items to queryset.

        The annotations are built from the 'admin_order_field' (column name)
        and 'annotation' (aggregate function) attribute of the callable.
        Returns the annotated queryset.
        """
        ordering = queryset.query.order_by
        for list_item in self.get_list_display(request):
            func = resolve_list_display_item(self, list_item)
            try:
                queryset = queryset.annotate(
                    **{func.admin_order_field: func.annotation}
                )
            except (AttributeError, exceptions.FieldError):
                # At least one necessary attribute to build the annotation
                # is missing. Or the aggregate function refers to an unknown
                # model field. Ignore this list_item.
                pass
        # Explicitly reapply the ordering;
        # django throws a RemovedInDjango31Warning when relying on
        # model.Meta.ordering for GROUP BY queries
        # (annotate() followed by values()).
        return queryset.order_by(*ordering)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return self._annotate_for_list_display(request, queryset)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = make_widget(model=db_field.related_model)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changelist(self, request, **kwargs):
        return MIZChangeList

    def get_index_category(self):
        """Return the index category of this ModelAdmin.

        Called by MIZAdminSite to create 'fake' apps for grouping purposes.
        """
        return self.index_category

    def get_actions(self, request):
        """
        Return a dictionary mapping of action_name: (callable, name, description)
        for this ModelAdmin for every action that the user has access to.
        """
        # TODO: django has _filter_actions_by_permissions
        actions = super().get_actions(request)

        for func, name, _desc in actions.copy().values():
            if name == 'delete_selected':
                # The builtin action 'delete_selected' is set by the admin site.
                perm_required = ['delete']
            else:
                perm_required = getattr(func, 'perm_required', [])

            for p in perm_required:
                perm_passed = False
                if callable(p):
                    perm_passed = p(self, request)
                else:
                    perm = '{}.{}'.format(
                        self.opts.app_label,
                        get_permission_codename(p, self.opts)
                    )
                    perm_passed = request.user.has_perm(perm)
                if not perm_passed:
                    del actions[name]
        return actions

    def get_exclude(self, request, obj=None):
        """Exclude all concrete M2M fields as those are handled by inlines."""
        self.exclude = super().get_exclude(request, obj)
        if self.exclude is None:
            self.exclude = []
            for fld in self.opts.get_fields():
                if fld.concrete and fld.many_to_many:
                    self.exclude.append(fld.name)
        return self.exclude

    def _add_bb_fieldset(self, fieldsets):
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
            fieldsets.append((
                'Beschreibung & Bemerkungen', {
                    'fields': bb_fields,
                    'classes': ['collapse', 'collapsed']
                }
            ))
        default_fieldset['fields'] = fields
        return fieldsets

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return self._add_bb_fieldset(fieldsets)

    def _add_pk_search_field(self, search_fields):
        """
        Add a search field ('pk__iexact') for the primary key to the
        search fields if it is missing.
        If the primary key is a OneToOneRelation, add 'pk__pk__iexact' instead.

        Returns an updated copy of the passed in search_fields list.
        """
        search_fields = search_fields.copy()
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

    def add_crosslinks(self, object_id, labels=None):
        """
        Provide the template with data to create links to related objects.

        Crosslinks are links on an instance's change form that send the user
        to the changelist containing the instance's related objects.
        """
        new_extra = {'crosslinks': []}
        labels = labels or {}

        inline_models = {i.model for i in self.inlines}
        # Walk through all reverse relations and create a crosslink for any
        # relation that is not covered by inlines.
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

            opts = query_model._meta
            count = query_model.objects.filter(**{query_field: object_id}).count()
            if not count:
                # No point showing an empty changelist.
                continue
            try:
                url = reverse(
                    "admin:{}_{}_changelist".format(opts.app_label, opts.model_name)
                )
            except NoReverseMatch:
                # NoReverseMatch, no link that leads anywhere!
                continue
            # Add the query string to the url:
            url += "?{field}={val}".format(
                field=query_field, val=str(object_id)
            )

            # Prepare the label for the link with the following priorities:
            #   - a passed in label
            #   - an explicitly declared related_name
            #       (unless the relation was automatically created,
            #       the default for related_name is None)
            #    - the verbose_name_plural of the related_model
            if opts.model_name in labels:
                label = labels[opts.model_name]
            elif rel.related_name:
                # Automatically created related_names won't look pretty!
                label = " ".join(
                    capfirst(s)
                    for s in rel.related_name.replace('_', ' ').split()
                )
            else:
                label = opts.verbose_name_plural

            label = "{label} ({count})".format(
                label=label, count=str(count)
            )
            new_extra['crosslinks'].append({'url': url, 'label': label})
        return new_extra

    @property
    def media(self):
        media = super().media
        if self.googlebtns:
            # utils.js contains the googlebtns script
            # TODO: remove this bit once googlebtns are handled by widgets
            return media + forms.Media(js=['admin/js/utils.js'])
        return ensure_jquery(media)

    def add_extra_context(self, request=None, extra_context=None, object_id=None):
        new_extra = extra_context or {}
        if object_id:
            new_extra.update(self.add_crosslinks(object_id, self.crosslink_labels))
        new_extra['collapse_all'] = self.collapse_all
        # TODO: remove this once googlebtns are handled by widgets
        new_extra['googlebtns'] = self.googlebtns
        if request:
            # TODO: why do we need 'request' in the context?
            new_extra['request'] = request
        return new_extra

    def add_view(self, request, form_url='', extra_context=None):
        new_extra = self.add_extra_context(
            request=request, extra_context=extra_context
        )
        return super().add_view(request, form_url, new_extra)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        new_extra = self.add_extra_context(
            request=request, extra_context=extra_context,
            object_id=object_id
        )
        return super().change_view(request, object_id, form_url, new_extra)

    def construct_change_message(self, request, form, formsets, add=False):
        """
        Construct a JSON structure describing changes from a changed object.

        Translations are deactivated so that strings are stored untranslated.
        Translation happens later on LogEntry access.
        """
        # TODO: WIP
        change_message = []
        if add:
            change_message.append({'added': {}})
        elif form.changed_data:
            change_message.append(
                {'changed': {'fields': form.changed_data}}
            )

        if formsets:
            with translation_override(None):
                for formset in formsets:
                    for added_object in formset.new_objects:
                        msg = self._construct_m2m_change_message(added_object)
                        change_message.append({'added': msg})
                    for changed_object, changed_fields in formset.changed_objects:
                        msg = self._construct_m2m_change_message(changed_object)
                        msg['fields'] = changed_fields
                        change_message.append({'changed': msg})
                    for deleted_object in formset.deleted_objects:
                        msg = self._construct_m2m_change_message(deleted_object)
                        change_message.append({'deleted': msg})
        return change_message

    def _construct_m2m_change_message(self, obj):
        """
        Construct a more useful change message for m2m objects of auto created models.
        """
        # TODO: WIP
        if obj._meta.auto_created:
            # An auto_created m2m through table only has two relation fields
            relation_field = [
                fld
                for fld in obj._meta.get_fields()
                if fld.is_relation and fld.related_model != self.model
            ][0]
            return {
                'name': force_text(relation_field.related_model._meta.verbose_name),
                'object': force_text(getattr(obj, relation_field.name)),
            }
        else:
            return {
                'name': force_text(obj._meta.verbose_name),
                'object': force_text(obj),
            }

    def has_module_permission(self, request):
        if self.superuser_only:
            # Hide the associated models from the index if
            # the current user is not a superuser
            return request.user.is_superuser
        return super().has_module_permission(request)

    def save_model(self, request, obj, form, change):
        if isinstance(obj, ComputedNameModel):
            # Delay the update of the _name until ModelAdmin._changeform_view
            # has saved the related objects via save_related. This is to avoid
            # update_name building a name with outdated related objects.
            # TODO: set obj._changed_flag = False to disable updates entirely?
            obj.save(update=False)
        else:
            super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if isinstance(form.instance, ComputedNameModel):
            # Update the instance's _name now. save_model was called earlier.
            # TODO: use the form and formsets to figure out if an update is required
            form.instance.update_name(force_update=True)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if 'adminform' in context:
            # Move checkbox widget to the right of its label.
            context['adminform'] = MIZAdminFormWrapper(context['adminform'])
        if 'media' in context:
            # Fix jquery load order during the add/change view process. If the
            # ModelAdmin does not have inlines, collapse elements will not work:
            # django's Fieldsets will include just 'collapse.js' if collapse is in the
            # fieldset's classes. django's AdminForm then scoops up all the Fieldsets
            # and merges their media with its own (which may just be nothing).
            # Finally, this ModelAdmin will merge its media [jquery.js, jquery_init.js, ...]
            # with that of the AdminForm. Since merging/sorting is now stable the
            # result will be [jquery.js, collapse.js, jquery_init.js, ...].
            # Usually this faulty load order is then later fixed by media mergers on the
            # inlines which mostly only have [jquery.js, jquery_init.js], but if the
            # ModelAdmin does not have any inlines, collapse will not work.
            context['media'] = ensure_jquery(context['media'])
        return super().render_change_form(
            request, context, add, change, form_url, obj)


class BaseInlineMixin(object):
    """
    A mixin for inline classes.

    It overrides the formfields for ForeignKeys, adds an optional 'description'
    and simplifies the assignment of verbose_name and verbose_name_plural.
    Sets extra for formsets to 1.

    Attributes:
        verbose_model (model class): the model whose verbose_name and
            verbose_name_plural attributes will be used to override
            this inline's default ones.
        description (str): short description of this inline in relation to its
            parent ModelAdmin.
    """

    verbose_model = None
    extra = 1
    classes = ['collapse']
    description = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.verbose_model:
            self.verbose_name = self.verbose_model._meta.verbose_name
            self.verbose_name_plural = self.verbose_model._meta.verbose_name_plural

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = make_widget(model=db_field.related_model)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class BaseTabularInline(BaseInlineMixin, admin.TabularInline):
    pass


class BaseStackedInline(BaseInlineMixin, admin.StackedInline):
    pass


class BaseAliasInline(BaseTabularInline):
    verbose_name_plural = 'Alias'


class BaseGenreInline(BaseTabularInline):
    verbose_model = _models.genre


class BaseSchlagwortInline(BaseTabularInline):
    verbose_model = _models.schlagwort


class BaseAusgabeInline(BaseTabularInline):
    form = AusgabeMagazinFieldForm
    verbose_model = _models.ausgabe
    fields = ['ausgabe__magazin', 'ausgabe']


class BaseOrtInLine(BaseTabularInline):
    verbose_name = 'Ort'
    verbose_name_plural = 'Assoziierte Orte'
