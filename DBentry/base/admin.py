from django import forms
from django.contrib import admin
from django.contrib.auth import get_permission_codename
from django.db import models
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
from DBentry.utils import get_model_relations,  ensure_jquery

class MIZModelAdmin(MIZAdminSearchFormMixin, admin.ModelAdmin):

    flds_to_group = []                      # Group these fields in a line; the group is inserted into the first formfield encountered
                                            # that matches a field in the group
    googlebtns = []                         # Fields in this list get a little button that redirect to a google search page #TODO: need to unquote the field value => Pascal „Cyrex“ Beniesch: Pascal %u201ECyrex%u201C Beniesch
    collapse_all = False                    # Whether to collapse all inlines/fieldsets by default or not
    hint = ''                               # A hint displayed at the top of the form #NOTE: is this hint even used by anything?: yes, DateiAdmin
    crosslink_labels = {}                   # Override the labels given to crosslinks: {'model_name': 'custom_label'}
    superuser_only = False                  # If true, only a superuser can interact with this ModelAdmin
    actions = [merge_records]

    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs=ATTRS_TEXTAREA)},
    }

    index_category = 'Sonstige'             # The name of the 'category' this ModelAdmin should be listed under on the index page

    #TODO: let the MIZ changelist template extend the default one 
    #change_list_template = 'miz_changelist.html'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return self._annotate_for_list_display(queryset)

    def _annotate_for_list_display(self, queryset):
        """
        Hook to add annotations to the root queryset of this ModelAdmin to allow ordering of callable list display items.
        """
        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = make_widget(model=db_field.related_model)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changelist(self, request, **kwargs):
        return MIZChangeList

    def get_index_category(self):
        # Should technically be different apps..
        return self.index_category

    def get_actions(self, request):
        # Show actions based on user permissions
        actions = super().get_actions(request) # returns an OrderedDict( (name, (func, name, desc)) )

        for func, name, desc in actions.copy().values():
            if name == 'delete_selected':
                perm_required = ['delete'] # the builtin action delete_selected is set by the admin site
            else:
                perm_required = getattr(func, 'perm_required', [])

            for p in perm_required:
                perm_passed = False
                if callable(p):
                    perm_passed = p(self, request)
                else:
                    perm = '{}.{}'.format(self.opts.app_label, get_permission_codename(p, self.opts))
                    perm_passed = request.user.has_perm(perm)
                if not perm_passed:
                    del actions[name]
        return actions

    def get_exclude(self, request, obj = None):
        # Exclude all m2m fields, as those are handled by inlines
        # reverse related fields will be sorted out by the ModelForm (django.forms.models.fields_for_model)
        self.exclude = super().get_exclude(request, obj)
        if self.exclude is None:
            self.exclude = []
            for fld in self.opts.get_fields():
                if fld.concrete and fld.many_to_many:
                    self.exclude.append(fld.name)
        return self.exclude

    def get_fields(self, request, obj = None):
        if not self.fields:
            self.fields = super().get_fields(request, obj)
            if self.flds_to_group:
                self.fields = self.group_fields()
        return self.fields

    def group_fields(self):
        if not self.fields:
            return []
        grouped_fields = self.fields
        fields_used = set()
        for tpl in self.flds_to_group:
            # Find the correct spot to insert the tuple into,
            # which would be the earliest occurence of any field of tuple in self.fields
            if any(f in fields_used for f in tpl):
                # To avoid duplicate fields, ignore tuples that contain any field we have already grouped
                continue
            indexes = [self.fields.index(f) for f in tpl if f in self.fields]
            if not indexes:
                # None of the fields in the tuple are actually in self.fields
                continue
            target_index = min(indexes)
            grouped_fields[target_index] = tpl
            indexes.remove(target_index)
            # Remove all other fields of the tuple that are in self.fields
            for i in indexes:
                grouped_fields.pop(i)
            fields_used.update(tpl) 
        return grouped_fields

    def get_fieldsets(self, request, obj=None):
        #TODO: this doesn't check if there is already a fieldset containing Beschreibung & Bemerkungen
        if self.fieldsets:
            return self.fieldsets
        fields = self.get_fields(request, obj).copy()
        fieldsets = [(None, {'fields': fields})]
        bb_fields = []
        if 'beschreibung' in fields:
            bb_fields.append(fields.pop(fields.index('beschreibung')))
        if 'bemerkungen' in fields:
            bb_fields.append(fields.pop(fields.index('bemerkungen')))
        if bb_fields:
            fieldsets.append(('Beschreibung & Bemerkungen', {'fields' : bb_fields, 'classes' : ['collapse', 'collapsed']}))
        return fieldsets

    def get_search_fields(self, request=None):
        # Replace the first primary key search field with an __iexact primary key lookup or append one if missing.
        # Remove all duplicates of primary key search fields.
        search_fields = list(self.search_fields or self.model.get_search_fields())
        if self.model._meta.pk.get_lookup('iexact') is None:
            # the pk field does not support iexact lookups (most likely a related field) and
            # ModelAdmin.get_search_results.construct_search tacks on the __iexact lookup, which will result in an error
            # This is fixed in later versions of django.
            # Models that rely on OneToOneFields (BaseBrochure, etc.) as their primary key can thus not support admin lookups for their pk.
            return search_fields
        pk_found = False
        pk_name = self.model._meta.pk.name
        for search_field in search_fields[:]:
            if search_field in ('pk', '=pk', pk_name, '=' + pk_name):
                if not pk_found:
                    search_fields[search_fields.index(search_field)] = '=pk'
                else:
                    search_fields.remove(search_field)
                pk_found = True
        if not pk_found:
            search_fields.append('=pk')
        return search_fields

    def add_crosslinks(self, object_id, labels = None):
        """
        Provides the template with data to create links to related objects.
        """
        new_extra = {'crosslinks':[]}
        labels = labels or {}

        inline_models = {i.model for i in self.inlines}
        # m2m self relations:
        #   will be 'ignored' as a inline must be used to facilitate that relation (i.e. query_model inevitably shows up in inline_models)
        # m2o self relations (rel.model == rel.related_model): 
        #   query_model == rel.model == rel.related_model; differentiating between them is pointless

        for rel in get_model_relations(self.model, forward = False, reverse = True):
            query_model = rel.related_model
            query_field = rel.remote_field.name
            if rel.many_to_many:
                inline_model = rel.through
                if rel.field.model == self.model and rel.model != rel.related_model:
                    # ManyToManyField lives on self.model and it is NOT a self relation. 
                    # Target the 'other end' of the relation - otherwise we would create a crosslink that leads back to self.model's changelist.
                    query_model = rel.model
                    query_field = rel.name
            else:
                inline_model = rel.related_model
            if inline_model in inline_models:
                continue
            count = query_model.objects.filter(**{query_field:object_id}).count()
            opts = query_model._meta
            if not count:
                # No point showing an empty changelist.
                continue
            try:
                url = reverse("admin:{}_{}_changelist".format(opts.app_label, opts.model_name)) \
                                + "?" + query_field + "=" + str(object_id)
            except NoReverseMatch:
                # NoReverseMatch, no link that leads anywhere!
                continue

            # Prepare the label for the link with the following priorities:
            # - a passed in label 
            # - an explicitly (as the default for it is None unless automatically created) declared related_name
            # - the verbose_name_plural of the related_model
            if opts.model_name in labels:
                label = labels[opts.model_name]
            elif rel.related_name:
                # Automatically created related_names won't look pretty!
                label = " ".join(capfirst(s) for s in rel.related_name.replace('_', ' ').split())
            else:
                label = opts.verbose_name_plural
            label += " ({})".format(str(count))
            new_extra['crosslinks'].append( dict(url=url, label=label) )
        return new_extra

    @property
    def media(self):
        media = super().media
        if self.googlebtns:
            return media + forms.Media(js = ['admin/js/utils.js']) # contains the googlebtns script
        return ensure_jquery(media)

    def add_extra_context(self, request = None, extra_context = None, object_id = None):
        new_extra = extra_context or {}
        if object_id:
            new_extra.update(self.add_crosslinks(object_id, self.crosslink_labels))
        new_extra['collapse_all'] = self.collapse_all
        new_extra['hint'] = self.hint
        new_extra['googlebtns'] = self.googlebtns
        if request:
            new_extra['request'] = request
        return new_extra

    def add_view(self, request, form_url='', extra_context=None):
        new_extra = self.add_extra_context(request = request, extra_context = extra_context)
        return super().add_view(request, form_url, new_extra)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        new_extra = self.add_extra_context(request = request, extra_context = extra_context, object_id = object_id)
        return super().change_view(request, object_id, form_url, new_extra)

    def construct_change_message(self, request, form, formsets, add=False):
        """
        Construct a JSON structure describing changes from a changed object.
        Translations are deactivated so that strings are stored untranslated.
        Translation happens later on LogEntry access.
        """
        #TODO: WIP
        change_message = []
        if add:
            change_message.append({'added': {}})
        elif form.changed_data:
            change_message.append({'changed': {'fields': form.changed_data}})

        if formsets:
            with translation_override(None):
                for formset in formsets:
                    for added_object in formset.new_objects:
                        change_message.append({'added': self._construct_m2m_change_message(added_object)})
                    for changed_object, changed_fields in formset.changed_objects:
                        msg = self._construct_m2m_change_message(changed_object)
                        msg['fields'] = changed_fields
                        change_message.append({'changed': msg})
                    for deleted_object in formset.deleted_objects:
                        change_message.append({'deleted': self._construct_m2m_change_message(deleted_object)})
        return change_message

    def _construct_m2m_change_message(self, obj):
        """
        Construct a more useful change message for m2m objects of auto created models.
        """
        #TODO: WIP
        if obj._meta.auto_created:
            # An auto_created m2m through table only has two relation fields
            relation_field = [fld for fld in obj._meta.get_fields() if fld.is_relation and fld.related_model != self.model][0]
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
            # Hide the associated models from the index if the current user is not a superuser
            return request.user.is_superuser
        return super().has_module_permission(request)

    def save_model(self, request, obj, form, change):
        if isinstance(obj, ComputedNameModel):
            # Delay the update of the _name until ModelAdmin._changeform_view has saved the related objects via save_related.
            # This is to avoid update_name building a name with outdated related objects.
            # TODO: set obj._changed_flag = False to disable updates entirely?
            obj.save(update=False)
        else:
            super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if isinstance(form.instance, ComputedNameModel):
            # Update the instance's _name now. save_model was called earlier.
            #TODO: use the form and formsets to figure out if an update is required
            form.instance.update_name(force_update=True)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        # Move checkbox widget to the right of its label.
        if 'adminform' in context:
            context['adminform'] = MIZAdminFormWrapper(context['adminform'])
        # Fix jquery load order during the add/change view process.
        # If the ModelAdmin does not have inlines, collapse elements will not work:
        # django's Fieldsets will include just 'collapse.js' if collapse is in the fieldset's classes.
        # django's AdminForm then scoops up all the Fieldsets and merges their media with its own
        # (which may just be nothing).
        # Finally, this ModelAdmin will merge its media [jquery.js, jquery_init.js, ...] with that of the AdminForm. 
        # Since merging/sorting is now stable the result will be [jquery.js, collapse.js, jquery_init.js, ...]
        # Usually this faulty load order is then later fixed by media mergers on the inlines which mostly only have 
        # [jquery.js, jquery_init.js], but if the ModelAdmin does not have any inlines, collapse will not work.
        if 'media' in context:
            context['media'] = ensure_jquery(context['media'])
        return super().render_change_form(request, context, add, change, form_url, obj)


class BaseInlineMixin(object):

    original = False
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


