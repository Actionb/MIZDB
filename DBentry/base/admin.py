from urllib.parse import urlencode, parse_qs

from django.contrib import admin
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_permission_codename
from django.utils.translation import override as translation_override
from django.utils.encoding import force_text
from django.utils.text import capfirst

from django import forms

from DBentry.models import ausgabe, genre, schlagwort, models
from DBentry.base.models import ComputedNameModel
from DBentry.changelist import MIZChangeList
from DBentry.forms import InLineAusgabeForm, FormBase
from DBentry.actions import merge_records
from DBentry.constants import SEARCH_TERM_SEP, ATTRS_TEXTAREA
from DBentry.ac.widgets import make_widget
from DBentry.helper import MIZAdminFormWrapper
from DBentry.utils import get_model_relations, parse_cl_querystring

class MIZModelAdmin(admin.ModelAdmin):
    
    flds_to_group = []                      # Group these fields in a line; the group is inserted into the first formfield encountered
                                            # that matches a field in the group
    googlebtns = []                         # Fields in this list get a little button that redirect to a google search page
    collapse_all = False                    # Whether to collapse all inlines/fieldsets by default or not
    hint = ''                               # A hint displayed at the top of the form 
    crosslink_labels = {}                   # Override the labels given to crosslinks: {'model_name': 'custom_label'}
    superuser_only = False                  # If true, only a superuser can interact with this ModelAdmin
    actions = [merge_records]
    
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs=ATTRS_TEXTAREA)},
    }
    
    index_category = 'Sonstige'             # The name of the 'category' this ModelAdmin should be listed under on the index page

    def has_adv_sf(self):
        return len(getattr(self, 'advanced_search_form', []))>0
            
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
        search_fields = self.search_fields or list(self.model.get_search_fields())
        # An extra 'pk' search field needs to be removed
        if 'pk' in search_fields:
            search_fields.remove('pk')
        # add __exact for pk lookups to enable searching for ids
        pk_name = self.model._meta.pk.name
        if "=" + pk_name in search_fields:
            pass
        elif pk_name in search_fields:
            search_fields.remove(pk_name)
            search_fields.append("=" + pk_name)
        else:
            search_fields.append("=" + pk_name)
        return search_fields
        
    def add_crosslinks(self, object_id, labels=None):
        """
        Provides the template with data to create links to related objects.
        """
        new_extra = {'crosslinks':[]}
        labels = labels or []
        
        inline_models = {i.model for i in self.inlines}
        
        for rel in get_model_relations(self.model, forward = False):
            if rel.many_to_many:
                inline_model = rel.through
            else:
                inline_model = rel.related_model
            if inline_model in inline_models:
                continue
            model = rel.related_model
            opts = model._meta
            fld_name = rel.remote_field.name
            count = model.objects.filter(**{fld_name:object_id}).count()
            if not count:
                continue
            try:
                url = reverse("admin:{}_{}_changelist".format(opts.app_label, opts.model_name)) \
                                + "?" + fld_name + "=" + str(object_id)
            except NoReverseMatch:
                continue
            if opts.model_name in labels:
                label = labels[opts.model_name]
            elif rel.related_name:
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
            media.add_js(['admin/js/utils.js']) # contains the googlebtns script
        return media
        
    def add_extra_context(self, extra_context = None, object_id = None):
        new_extra = extra_context or {}
        if object_id:
            new_extra.update(self.add_crosslinks(object_id, self.crosslink_labels))
        new_extra['collapse_all'] = self.collapse_all
        new_extra['hint'] = self.hint
        new_extra['googlebtns'] = self.googlebtns
        return new_extra
        
    def add_view(self, request, form_url='', extra_context=None):
        new_extra = self.add_extra_context(extra_context)
        return self.changeform_view(request, None, form_url, new_extra)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        new_extra = self.add_extra_context(extra_context, object_id)
        return super().change_view(request, object_id, form_url, new_extra)
        
    def lookup_allowed(self, key, value):
        if self.has_adv_sf():
            # allow lookups defined in advanced_search_form
            for list in getattr(self, 'advanced_search_form').values():
                if key in list:
                    return True
        if key in [i[0] if isinstance(i, tuple) else i for i in self.list_filter]:
            # allow lookups defined in list_filter
            return True
        return super().lookup_allowed(key, value)    
        
    def get_preserved_filters(self, request):
        """
        Update the querystring for the changelist with possibly new date from the form the user has 
        sent.
        """
        preserved_filters =  super().get_preserved_filters(request) #'_changelist_filters=ausgabe__magazin%3D326%26ausgabe%3D14962'

        if not (request.POST and '_changelist_filters' in request.GET):
            # Either this is request has no POST or no filters were used on the changelist
            return preserved_filters
            
        # Decode the preserved_filters string to get the keys and values that were used to filter with back
        filter_items = parse_cl_querystring(preserved_filters)
        for k, v in filter_items.copy().items():
            if k in request.POST and request.POST[k]:
                # This changelist filter shows up in request.POST, the user may have changed its value
                filter_items[k] = request.POST[k] 
            
            # Flatten the lists of values
            if isinstance(filter_items[k], list) and len(filter_items[k]) == 1:
                filter_items[k] = filter_items[k][0]
        preserved_filters = parse_qs(preserved_filters) 
        preserved_filters['_changelist_filters'] = urlencode(sorted(filter_items.items()))
        return urlencode(preserved_filters)
        
        
    def get_changeform_initial_data(self, request):
        """ Turn _changelist_filters string into a useable dict of field_path:value
            so we can fill some formfields with initial values later on. 
            IMPORTANT: THIS ONLY GOVERNS FORMFIELDS FOR ADD-VIEWS. 
            Primarily used for setting ausgabe/magazin for Artikel add-views.
        """
        initial = super().get_changeform_initial_data(request)
        if '_changelist_filters' not in initial or not initial['_changelist_filters']:
            return initial
            
        # At this point, _changelist_filters is a string of format:
        # '_changelist_filters': 'ausgabe__magazin=47&ausgabe=4288'
        # SEARCH_TERM_SEP: '='
        filter_dict = {}
        for part in initial['_changelist_filters'].split('&'):
            if part and SEARCH_TERM_SEP in part:
                if part.startswith("q="):
                    # This part is a string typed into the searchbar, ignore it
                    continue
                try:
                    k, v = part.split(SEARCH_TERM_SEP)
                except ValueError:
                    continue
                if k not in initial:
                    filter_dict[k] = v
        initial.update(filter_dict)
        return initial
        
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
        return True

    def save_model(self, request, obj, form, change):
        if isinstance(obj, ComputedNameModel):
            # Delay the update of the _name until ModelAdmin._changeform_view has saved the related objects via save_related.
            # This is to avoid update_name building a name with outdated related objects.
            obj.save(update=False)
        else:
            super().save_model(request, obj, form, change)
        
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if isinstance(form.instance, ComputedNameModel):
            # Update the instance's _name now. save_model was called earlier.
            form.instance.update_name(force_update=True)
    
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        # Move checkbox widget to the right of its label.
        if 'adminform' in context:
            context['adminform'] = MIZAdminFormWrapper(context['adminform'])
        return super().render_change_form(request, context, add, change, form_url, obj)

        
class BaseInlineMixin(object):
    
    original = False
    verbose_model = None
    extra = 1
    classes = ['collapse']
    form = FormBase # For the validate_unique override
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
    verbose_model = genre
    
class BaseSchlagwortInline(BaseTabularInline):
    verbose_model = schlagwort
    
class BaseAusgabeInline(BaseTabularInline):
    form = InLineAusgabeForm
    verbose_model = ausgabe
    fields = ['ausgabe__magazin', 'ausgabe']
    
class BaseOrtInLine(BaseTabularInline):
    verbose_name = 'Ort'
    verbose_name_plural = 'Assoziierte Orte'
    

