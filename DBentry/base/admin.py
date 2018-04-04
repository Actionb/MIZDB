from django.contrib import admin
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_permission_codename

from DBentry.changelist import MIZChangeList
from DBentry.forms import makeForm
from DBentry.actions import *
from DBentry.constants import SEARCH_TERM_SEP


class MIZModelAdmin(admin.ModelAdmin):
    
    form = None                             # None rather than BaseModelAdmin's default ModelForm, so we can use either 
                                            # custom form classes or the new implicit default makeForm function
    flds_to_group = []                      # Group these fields in a line; the group is inserted into the first formfield encountered
                                            # that matches a field in the group
    googlebtns = []                         # Fields in this list get a little button that redirect to a google search page
    collapse_all = False                    # Whether to collapse all inlines/fieldsets by default or not
    hint = ''                               # A hint displayed at the top of the form 
    actions = [merge_records]

    def has_adv_sf(self):
        return len(getattr(self, 'advanced_search_form', []))>0
    
    def get_form(self, *args, **kwargs):
        if self.form is None:
            self.form = makeForm(self.model)
        return super().get_form(*args, **kwargs)
    
    def get_changelist(self, request, **kwargs):
        return MIZChangeList
        
    def get_actions(self, request):
        # Show actions based on user permissions
        actions = super(ModelBase, self).get_actions(request) # returns an OrderedDict( (name, (func, name, desc)) )
        
        for func, name, desc in actions.values():
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
        # Exclude all fields that are a reverse relation to this model, as those are handled by inlines
        self.exclude = super(ModelBase, self).get_exclude(request, obj)
        if self.exclude is None:
            self.exclude = []
            for fld in self.opts.get_fields():
                if self.model.get_reverse_relations():
                    self.exclude.append(fld.name)
        return self.exclude
    
    def get_fields(self, request, obj = None):
        if not self.fields:
            self.fields = super(ModelBase, self).get_fields(request, obj)
            if self.flds_to_group:
                self.fields = self.group_fields()
        return self.fields
        
    def group_fields(self):
        if not self.fields:
            return []
        grouped_fields = self.fields
        for tpl in self.flds_to_group:
            # Find the correct spot to insert the tuple into,
            # which would be the earliest occurence of any field of tuple in self.fields
            indexes = [self.fields.index(i) for i in tpl if i in self.fields]
            if not indexes:
                # None of the fields in the tuple are actually in self.fields
                continue
            target_index = min(indexes)
            grouped_fields[target_index] = tpl
            indexes.remove(target_index)
            # Remove all other fields of the tuple that are in self.fields
            for i in indexes:
                grouped_fields.pop(i)
        return grouped_fields
    
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
        
    def add_crosslinks(self, object_id):
        """
        Provides the template with data to create links to related objects.
        """
        new_extra = {'crosslinks':[]}
        
        inlmdls = {i.model for i in self.inlines}
        for rel in (r for r in self.model.get_reverse_relations() if r.related_model not in inlmdls):
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
            label = opts.verbose_name_plural + " ({})".format(str(count))
            new_extra['crosslinks'].append( dict(url=url, label=label) )
        return new_extra
        
    @property
    def media(self):
        media = super(ModelBase, self).media
        if self.googlebtns:
            media.add_js(['admin/js/utils.js'])
        return media
        
    def add_extra_context(self, extra_context = None, object_id = None):
        new_extra = extra_context or {}
        if object_id:
            new_extra.update(self.add_crosslinks(object_id))
        new_extra['collapse_all'] = self.collapse_all
        new_extra['hint'] = self.hint
        new_extra['googlebtns'] = self.googlebtns
        return new_extra
        
    def add_view(self, request, form_url='', extra_context=None):
        new_extra = self.add_extra_context(extra_context)
        return self.changeform_view(request, None, form_url, new_extra)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        new_extra = self.add_extra_context(extra_context, object_id)
        return super(ModelBase, self).change_view(request, object_id, form_url, new_extra)
        
    def lookup_allowed(self, key, value):
        if self.has_adv_sf():
            # allow lookups defined in advanced_search_form
            for list in getattr(self, 'advanced_search_form').values():
                if key in list:
                    return True
        if key in [i[0] if isinstance(i, tuple) else i for i in self.list_filter]:
            # allow lookups defined in list_filter
            return True
        return super(ModelBase, self).lookup_allowed(key, value)
        
    def get_changeform_initial_data(self, request):
        """ Turn _changelist_filters string into a useable dict of field_path:value
            so we can fill some formfields with initial values later on. 
            IMPORTANT: THIS ONLY GOVERNS FORMFIELDS FOR ADD-VIEWS. 
            Primarily used for setting ausgabe/magazin for Artikel add-views.
        """
        initial = super(ModelBase, self).get_changeform_initial_data(request)
        if '_changelist_filters' not in initial.keys() or not initial['_changelist_filters']:
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
                if k not in initial.keys():
                    filter_dict[k] = v
        initial.update(filter_dict)
        return initial
        
    def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
        # Add a description to each formset
        inline_admin_formsets = super(ModelBase, self).get_inline_formsets(request, formsets, inline_instances, obj)
        for formset in inline_admin_formsets:
            formset.description = getattr(formset.opts, 'description', '')
        return inline_admin_formsets
        
class BaseInlineMixin(object):
    
    form = None                             # None rather than BaseModelAdmin's default ModelForm, so we can use either 
                                            # custom form classes or the new implicit default makeForm function
    original = False
    verbose_model = None
    extra = 1
    classes = ['collapse']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.verbose_model:
            self.verbose_name = self.verbose_model._meta.verbose_name
            self.verbose_name_plural = self.verbose_model._meta.verbose_name_plural
    
    def get_formset(self, *args, **kwargs):
        if self.form is None:
            self.form = makeForm(self.model)
        return super().get_formset(*args, **kwargs)
        
class BaseTabularInline(BaseInlineMixin, admin.TabularInline):
    pass
            
class BaseStackedInline(BaseInlineMixin, admin.StackedInline):
    pass

class BaseAliasInline(BaseTabularInline):
    verbose_name_plural = 'Alias'
    
class BaseGenreInline(BaseTabularInline):
    extra = 1
    verbose_name = genre._meta.verbose_name
    verbose_name_plural = genre._meta.verbose_name_plural
    
class BaseSchlagwortInline(BaseTabularInline):
    extra = 1
    verbose_name = schlagwort._meta.verbose_name
    verbose_name_plural = schlagwort._meta.verbose_name_plural
