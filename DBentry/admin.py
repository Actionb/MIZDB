from django.contrib import admin, messages
from django.forms import modelform_factory, inlineformset_factory, Textarea
from django.core.exceptions import FieldDoesNotExist
from django.utils.html import format_html

from .models import *
from .helper import *
from .constants import *
from .forms import *
from .utils import link_list
from .filters import RelatedOnlyDropdownFilter

from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter

from django.contrib.admin.views.main import *

class MIZChangeList(ChangeList):
    
    def get_filters(self, request):
        lookup_params = self.get_filters_params()
        use_distinct = False

        for key, value in lookup_params.items():
            if not self.model_admin.lookup_allowed(key, value):
                raise DisallowedModelAdminLookup("Filtering by %s not allowed" % key)

        filter_specs = []
        if self.list_filter:
            for list_filter in self.list_filter:
                if callable(list_filter):
                    # This is simply a custom list filter class.
                    spec = list_filter(request, lookup_params, self.model, self.model_admin)
                else:
                    field_path = None
                    if isinstance(list_filter, (tuple, list)):
                        # This is a custom FieldListFilter class for a given field.
                        field, field_list_filter_class = list_filter
                    else:
                        # This is simply a field name, so use the default
                        # FieldListFilter class that has been registered for
                        # the type of the given field.
                        field, field_list_filter_class = list_filter, FieldListFilter.create
                    if not isinstance(field, models.Field):
                        field_path = field
                        field = get_fields_from_path(self.model, field_path)[-1]

                    lookup_params_count = len(lookup_params)
                    spec = field_list_filter_class(
                        field, request, lookup_params,
                        self.model, self.model_admin, field_path=field_path
                    )
                    # field_list_filter_class removes any lookup_params it
                    # processes. If that happened, check if distinct() is
                    # needed to remove duplicate results.
                    if lookup_params_count > len(lookup_params):
                        use_distinct = use_distinct or lookup_needs_distinct(self.lookup_opts, field_path)
                if spec and spec.has_output():
                    filter_specs.append(spec)

        # At this point, all the parameters used by the various ListFilters
        # have been removed from lookup_params, which now only contains other
        # parameters passed via the query string. We now loop through the
        # remaining parameters both to ensure that all the parameters are valid
        # fields and to determine if at least one of them needs distinct(). If
        # the lookup parameters aren't real fields, then bail out.
        try:
            remaining_lookup_params = dict()
            for key, value in lookup_params.items():
                if key in self.model_admin.search_fields_redirect:
                    qobject = models.Q()
                    for redirect in self.model_admin.search_fields_redirect.get(key, []):
                    #TODO: if callable etc
                        qobject |= models.Q( (redirect, prepare_lookup_value(redirect, value)) )
                        use_distinct = use_distinct or lookup_needs_distinct(self.lookup_opts, redirect)
                    remaining_lookup_params[key] = qobject
                else:
                    remaining_lookup_params[key] = prepare_lookup_value(key, value)
                    use_distinct = use_distinct or lookup_needs_distinct(self.lookup_opts, key)
            return filter_specs, bool(filter_specs), remaining_lookup_params, use_distinct
        except FieldDoesNotExist as e:
            six.reraise(IncorrectLookupParameters, IncorrectLookupParameters(e), sys.exc_info()[2])
            
    
    def get_queryset(self, request):
        """ Copy pasted from original ChangeList to switch around ordering and filtering.
            Also allowed the usage of Q items to filter the queryset.
        """
        # First, we collect all the declared list filters.
        (self.filter_specs, self.has_filters, remaining_lookup_params,
         filters_use_distinct) = self.get_filters(request)

        # Then, we let every list filter modify the queryset to its liking.
        qs = self.root_queryset
        for filter_spec in self.filter_specs:
            new_qs = filter_spec.queryset(request, qs)
            if new_qs is not None:
                qs = new_qs

        try:
            # Finally, we apply the remaining lookup parameters from the query
            # string (i.e. those that haven't already been processed by the
            # filters).
            for k, v in remaining_lookup_params.items():
                if isinstance(v, models.Q):
                    qs = qs.filter(v)
                else:
                    qs = qs.filter(**{k:v})
            
        except (SuspiciousOperation, ImproperlyConfigured) as e:
            # Allow certain types of errors to be re-raised as-is so that the
            # caller can treat them in a special way.
            raise
        except Exception as e:
            # Every other error is caught with a naked except, because we don't
            # have any other way of validating lookup parameters. They might be
            # invalid if the keyword arguments are incorrect, or if the values
            # are not in the correct type, so we might get FieldError,
            # ValueError, ValidationError, or ?.
            raise IncorrectLookupParameters(e)

        if not qs.query.select_related:
            qs = self.apply_select_related(qs)
            
        # Apply search results
        qs, search_use_distinct = self.model_admin.get_search_results(request, qs, self.query)
       
        qs = qs.resultbased_ordering()
        # Set ordering.
        ordering = self.get_ordering(request, qs)
        qs = qs.order_by(*ordering)
        
        # Remove duplicates from results, if necessary
        if filters_use_distinct | search_use_distinct:
            return qs.distinct()
        else:
            return qs


class ModelBase(admin.ModelAdmin):
    
    def __init__(self, *args, **kwargs):
        super(ModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(self.model)
        if not self.search_fields:
            self.search_fields = list(self.model.get_search_fields())
        
    search_fields_redirect = dict()
    flds_to_group = []
    crosslinks = []
    gogglebtns = []
    
    def has_adv_sf(self):
        return getattr(self, 'advanced_search_form', False)
    
    def get_changelist(self, request, **kwargs):
        return MIZChangeList
    
    def get_exclude(self, request, obj = None):
        self.exclude = super(ModelBase, self).get_exclude(request, obj)
        if self.exclude is None:
            self.exclude = []
            for fld in self.opts.get_fields():
                if hasattr(fld, 'm2m_field_name'):
                    self.exclude.append(fld.name)
        return self.exclude
    
    def get_fields(self, request, obj = None):
        if not self.fields:
            self.fields = super(ModelBase, self).get_fields(request, obj)
            if self.flds_to_group:
                self.fields = self.group_fields()
        return self.fields
    
    def group_fields(self):
        if self.fields is None:
            return None
        fields = self.fields
        for tpl in self.flds_to_group:
            try:
                if tpl[0] in fields:
                    if len(tpl)==3 and tpl[-1] == 1:
                        # tuple has a third part which tells us which of the fields to group takes priority
                        fields[ fields.index(tpl[0])] = (tpl[1], tpl[0])
                    else:
                        fields[ fields.index(tpl[0])] = (tpl[0], tpl[1])
                if tpl[1] in fields:
                        fields.remove(tpl[1])
            except:
                pass
        return fields
    
    def get_search_fields(self, request=None):
        if self.search_fields:
            return self.search_fields
        return list(self.model.get_search_fields())
        
    def add_crosslinks(self, object_id):
        return {}
        # THE GENERIC WAY
        # WIP
        from django.contrib.admin.utils import reverse
        from django.db.models.fields.reverse_related import ManyToOneRel
        from django.db.models.fields.related import ManyToManyField
        new_extra = {}
        new_extra['crosslinks'] = []
        #rels = {i.related_model for i in self.model.get_m2mfields() if not isinstance(i, ManyToManyField)}
        inlmdls = {i.model for i in self.inlines}
#        rel_objs = {rel.related_model for rel in self.model.get_m2mfields() if isinstance(rel, ManyToOneRel)}
#        rel_objs = rel_objs - inlmdls
#        #print(rels - inlmdls)
        
        for rel in self.model.get_m2mfields():
            if isinstance(rel, ManyToOneRel) and rel.related_model not in [i.model for i in self.inlines]:
                    # We're only interested in reverse relations
                    # forward relations are returned of type django.db.models.fields.related.ManyToManyField and
                    # those are already being handled by the inlines
                model = rel.related_model
                fld_name = rel.remote_field.name
                try:
                    link = reverse("admin:{}_{}_changelist".format(self.opts.app_label, model._meta.model_name)) \
                                    + "?" + fld_name + "=" + object_id
                except:
                    continue
                count = model._default_manager.filter(**{fld_name:object_id}).count()
                
                label = model._meta.verbose_name_plural + "({})".format(count)
                new_extra['crosslinks'].append( dict(link=link, label=label) )
        return new_extra
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        new_extra = extra_context or {}
        new_extra.update(self.add_crosslinks(object_id))
        return super(ModelBase, self).change_view(request, object_id, form_url, extra_context   )
        
    def lookup_allowed(self, key, value):
        if self.has_adv_sf():
            for list in self.has_adv_sf().values():
                if key in list:
                    return True
        if key in [i[0] if isinstance(i, tuple) else i for i in self.list_filter]:
            return True
        return super(ModelBase, self).lookup_allowed(key, value)
            
    def resolve_search_field(self, field_name):
        search_fields = self.get_search_fields()
        
        if field_name[0] in ['^', '*', '<', '>']:
            field_name = field_name[1:]
        
        # Check for the field_name in redirects first
        if field_name in self.search_fields_redirect:
            return self.search_fields_redirect[field_name]
            
        # Next,try to find a full match in search_fields
        elif field_name in search_fields:
            return field_name
                
        # Lastly, try to find parts of it in search_fields
        elif any(s.find(field_name)!=-1 for s in search_fields):
            return [s for s in search_fields if s.find(field_name)!=-1][0]

            
    def get_search_results(self, request, queryset, search_term):
        # Overriden to allow search by keywords (seite=75,magazin=Good Times)
        
        def search_term_to_list(self, x, SEP=SEARCH_SEG_SEP):
            # constants: SEARCH_SEG_SEP = ',' ; SEARCH_TERM_SEP = '='
            
            xlist = [i.strip().split(SEARCH_TERM_SEP) for i in x.split(SEP)]
            
            rslt = []
            for i in xlist:
                if len(i)==1:
                    continue
                
                search_field = i[0].lower()
                # Check if the search_field is prefixed with a hint for field lookups
                if search_field.startswith('^'):
                    field_lookup = '__istartswith'
                elif search_field.startswith('*'):
                    field_lookup = '__iexact'
                elif search_field.startswith('>'):
                    field_lookup = '__gt'
                elif search_field.startswith('<'):
                    field_lookup = '__lt'
                else:
                    field_lookup = '__icontains'
                    
                if field_lookup != '__icontains':
                    search_field = search_field[1:]
                    
                # Resolve the search_field into a query-able term, found in either self.search_fields or self.search_fields_redirect
                resolved_search_field = self.resolve_search_field(search_field)
                if resolved_search_field:
                    if callable(resolved_search_field):
                        # the search_field points to a callable function, we will need to remember the original search_field for
                        # queryset prefixing. We do not need the field_lookup value, since, currently, the callable may apply a specific
                        # field_lookup of its own.
                        i[1] = search_field + '@' + i[1]
                        rslt.append((resolved_search_field, i[1]))
                    else:
                        rslt.append((resolved_search_field+field_lookup, i[1]))
            return rslt
        
        if not self.search_fields:
            self.search_fields = self.get_search_fields(request)
        qs, use_distinct = super(ModelBase, self).get_search_results(request, queryset, search_term)
        if search_term.find("=")!=-1:
            search_list = search_term_to_list(self, search_term)
            if search_list:
                for k, v in search_list:
                    if callable(k):
                        # key is a callable like strquery that would return a list of q items to filter with
                        # search_term_to_dict has changed the value into a string of format 'prefix@value'
                        prefix, value = (v.split('@'))
                        v = k(search_term=value, prefix=prefix+"__")
                        if v:
                            for q in v:
                                try:
                                    queryset = queryset.filter(*q)
                                except ValueError:
                                    continue
                    else:
                        qitem = models.Q( **{k:v} )
                        try:
                            queryset = queryset.filter(qitem)
                        except ValueError:
                            continue
                qs = queryset
        if not qs.exists():
            # Query returned no results.
            # Maybe the User was searching for a __str__ string of an object
            try:
                qs = self.model.strquery_as_queryset(search_term)
            except:
                pass
        return qs, use_distinct  
        
    def get_changeform_initial_data(self, request):
        """ Turn the mess of _changelist_filters of safe and unsafe http bits into a useable dict of field_path:value
            Subclasses are supposed to refine this further to provide initial data."""
        from django.utils.http import unquote
        initial = super(ModelBase, self).get_changeform_initial_data(request)
        if '_changelist_filters' not in initial.keys() or not initial['_changelist_filters']:
            return initial
        clfilter = initial['_changelist_filters']
        
        clfilter = clfilter.replace('&', SEARCH_SEG_SEP)
        clfilter = unquote(clfilter)
        
        filter_dict = {}
        for part in clfilter.split(SEARCH_SEG_SEP):
            if part and SEARCH_TERM_SEP in part:
                if part.startswith("q="):
                    part = part[2:]
                try:
                    k, v = part.split(SEARCH_TERM_SEP)
                except ValueError:
                    continue
                if k not in initial.keys():
                    filter_dict[k] = unquote(v).replace('+', ' ')
        # Maybe keep string _changelist_filters in the initial dict?    
        initial['_changelist_filters'] = filter_dict
        return initial


    def merge_records(self, request, queryset):
        if queryset.count() == 1:
            self.message_user(request,'Bitte mindestens zwei Datensätze auswählen.', 'warning')
            return
        original_pk = queryset.first().pk
        queryset = queryset.exclude(pk=original_pk)
        duplicates = [i.pk for i in queryset]
        queryset.model.merge(original_pk, duplicates, verbose = False)
    merge_records.short_description = 'Datensätze zusammenfügen'
    

class TabModelBase(admin.TabularInline):
    original = False
    verbose_model = None
    extra = 1
    def __init__(self, *args, **kwargs):
        super(TabModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(model = self.model)
        if self.verbose_model:
            self.verbose_name = self.verbose_model._meta.verbose_name
            self.verbose_name_plural = self.verbose_model._meta.verbose_name_plural

class AliasTabBase(TabModelBase):
    verbose_name_plural = 'Alias'
    
class BestandModelBase(TabModelBase):
    model = bestand
    readonly_fields = ['signatur']
    fields = ['signatur', 'lagerort', 'provenienz']
    verbose_name = bestand._meta.verbose_name
    verbose_name_plural = bestand._meta.verbose_name_plural
    
class GenreModelBase(TabModelBase):
    verbose_name = genre._meta.verbose_name
    verbose_name_plural = genre._meta.verbose_name_plural
    
class SchlagwortModelBase(TabModelBase):
    verbose_name = schlagwort._meta.verbose_name
    verbose_name_plural = schlagwort._meta.verbose_name_plural
    
    
@admin.register(audio)
class AudioAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    infields = [BestandInLine]

class BestandListFilter(admin.SimpleListFilter):
    title = "Bestand vorhanden"
    parameter_name = "bestand"
    
    def lookups(self, request, model_admin):
        lks = [('zraum','Zeitschriftenraum'),('nzraum','nicht im Zeitschriftenraum'),
                ('dubl', 'als Dublette'), ('ndubl', 'nicht als Dublette')]
        return lks
    
    def queryset(self, request, queryset):
        if self.value()=='zraum':
            return queryset.filter(bestand__lagerort_id=ZRAUM_ID)
        if self.value()=='dubl':
            return queryset.filter(bestand__lagerort_id=DUPLETTEN_ID)
        if self.value()=='nzraum':
            return queryset.exclude(bestand__lagerort_id=ZRAUM_ID)
        if self.value()=='ndubl':
            return queryset.exclude(bestand__lagerort_id=DUPLETTEN_ID)

@admin.register(ausgabe)
class AusgabenAdmin(ModelBase):
    class NumInLine(TabModelBase):
        model = ausgabe_num
        extra = 0
    class MonatInLine(TabModelBase):
        model = ausgabe_monat
        extra = 0
    class LNumInLine(TabModelBase):
        model = ausgabe_lnum
        extra = 0
    class JahrInLine(TabModelBase):
        model = ausgabe_jahr
        extra = 0
        verbose_name_plural = 'erschienen im Jahr'
    class BestandInLine(BestandModelBase):
        pass
    inlines = [NumInLine,  MonatInLine, LNumInLine, JahrInLine,BestandInLine,  ]
    flds_to_group = [('status', 'sonderausgabe')]
    
    list_display = ('__str__', 'num_string', 'lnum_string','monat_string','jahre', 'jahrgang', 
                        'magazin','e_datum','anz_artikel', 'status') 
    search_fields = ['magazin__magazin_name', 'status', 'e_datum', 
        'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr','ausgabe_monat__monat__monat']
    list_filter = [('magazin__magazin_name', DropdownFilter),('ausgabe_jahr__jahr', DropdownFilter), 'status',BestandListFilter, ]#('bestand__lagerort', BestandListFilter)]
    search_fields_redirect = { 
                            'bearbeitungsstatus' : 'status',
                            'nr' : 'ausgabe_num__num', 
                            'nummer' : 'ausgabe_num__num', 
                            'lfd' : 'ausgabe_lnum__lnum', 
                            }
                        
    actions = ['add_duplicate', 'add_bestand', 'merge_records', 'num_to_lnum', 'add_birgit', 'bulk_jg']
    advanced_search_form = {
        'gtelt':['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum'], 
        'selects':['status'], 
        'simple':['jahrgang', 'sonderausgabe']
    }
    crosslinks = [(artikel, 'ausgabe')]
       
    # ACTIONS
    def add_duplicate(self, request, queryset):
        try:
            dupletten_lagerort = lagerort.objects.get(pk = DUPLETTEN_ID)
        except:
            self.message_user(request, "Konnte keine Dubletten hinzufügen. Lagerort nicht gefunden.", 'error')
            return
        dupe_list = [bestand(ausgabe=i, lagerort=dupletten_lagerort) for i in queryset]
        try:
            bestand.objects.bulk_create(dupe_list)
        except:
            self.message_user(request, "Konnte keine Dubletten hinzufügen: Interner Fehler.", 'warning')
        else:
            obj_links = link_list(request, [d.ausgabe for d in dupe_list])
            msg_text = "Dublette(n) zu diesen {} Ausgaben hinzugefügt: {}".format(len(dupe_list), obj_links)
            self.message_user(request, format_html(msg_text))
    add_duplicate.short_description = 'Dubletten-Bestand hinzufügen'
    
    def add_bestand(self, request, queryset):
        try:
            zraum_lagerort = lagerort.objects.get(pk = ZRAUM_ID)
        except:
            self.message_user(request, "Konnte keinen Zeitschriftenraum-Bestand hinzufügen. Lagerort nicht gefunden.", 'error')
            return
        zraum_list = []
        dupe_list = []
        for instance in queryset:
            if not bestand.objects.filter(ausgabe=instance, lagerort=zraum_lagerort).exists():
                zraum_list.append(bestand(ausgabe=instance, lagerort=zraum_lagerort))
            else:
                try:
                    dupletten_lagerort = lagerort.objects.get(pk = DUPLETTEN_ID)
                except:
                    continue
                else:
                    dupe_list.append(bestand(ausgabe=instance, lagerort=dupletten_lagerort))
        
        if len(zraum_list):
            try: 
                bestand.objects.bulk_create(zraum_list)
            except:
                self.message_user(request, "Konnte keinen Bestand hinzufügen: Interner Fehler.", 'warning')
                return
        obj_links = link_list(request, [z.ausgabe for z in zraum_list])
        msg_text = "Zeitschriftenraum-Bestand zu diesen {} Ausgaben hinzugefügt: {}".format(len(zraum_list), obj_links)
        self.message_user(request, format_html(msg_text))
        if dupe_list:
            obj_links = link_list(request, [d.ausgabe for d in dupe_list])
            msg_text = 'Folgende {} Ausgaben hatten bereits einen Bestand im Zeitschriftenraum: {}'.format(
                        len(dupe_list), obj_links
                        )
            self.message_user(request, format_html(msg_text), 'warning')
            if AUTO_ASSIGN_DUPLICATE:
                try:
                    bestand.objects.bulk_create(dupe_list)
                except:
                    self.message_user(request, "Konnte keine Dubletten hinzufügen: Interner Fehler.", 'warning')
                else:
                    msg_text = "{} Dubletten hinzugefügt: {}".format(len(dupe_list), obj_links)
                    self.message_user(request, format_html(msg_text))
    add_bestand.short_description = 'Zeitschriftenraum-Bestand hinzufügen'
        
    def num_to_lnum(self, request, queryset):
        to_create = []
        for instance in queryset:
            for num in instance.ausgabe_num_set.values_list('num', flat = True):
                to_create.append(ausgabe_lnum(ausgabe=instance, lnum=num)) #**{'ausgabe':instance, 'lnum':num}
            instance.ausgabe_num_set.all().delete()
            instance.ausgabe_lnum_set.all().delete()
        ausgabe_lnum.objects.bulk_create(to_create)
        
    def add_birgit(self, request, queryset):
        birgit = provenienz.objects.get(pk=6)
        for instance in queryset:
            instance.bestand_set.update(provenienz=birgit)
            
    def bulk_jg(self, request, queryset):
        mag_id = queryset.values_list('magazin_id',  flat = True)
        if mag_id.count() != 1:
            msg_text = "Aktion abgebrochen: Ausgaben-Liste enthält mehr als ein Magazin."
            self.message_user(request, msg_text, 'error')
            return
        jg = 1
        if queryset.first().jahrgang:
            jg = queryset.first().jahrgang
        mag = magazin.objects.get(pk=mag_id)
        mag.ausgabe_set.bulk_add_jg(jg)
        
    # Have the right magazin selected in change_form
    def get_changeform_initial_data(self, request):
        #'ausgabe_jahr__jahr=1959&magazin__magazin_name=Backstreets&q=num%3D12'
        initial = super(AusgabenAdmin, self).get_changeform_initial_data(request)
        if '_changelist_filters' not in initial.keys():
            return initial
        filter_dict = initial['_changelist_filters']
        mag = None
        for key in filter_dict.keys():
            if key.find('magazin') != -1:
                mag = filter_dict[key]
                break
        if mag:
            if mag.isnumeric():
                try:
                    mag_instance = magazin.objects.get(pk=mag)
                except:
                    pass
                else:
                    initial['magazin'] = mag_instance
            else:
                try:
                    mag_instance = magazin.objects.get(magazin_name__icontains=mag)
                except:
                    pass
                else:
                    initial['magazin'] = mag_instance
        return initial
                
    
@admin.register(autor)
class AutorAdmin(ModelBase):
    class MagazinInLine(TabModelBase):
        model = autor.magazin.through
        extra = 1
    
    inlines = [MagazinInLine]
    
    list_display = ['__str__', 'magazin_string']
    search_fields = ['person__vorname', 'person__nachname', 'kuerzel']
    search_fields_redirect = {'vorname':'person__vorname', 'nachname':'person__nachname'}

    crosslinks = [(artikel, 'autor'), (buch, 'autor')]
    
@admin.register(artikel)
class ArtikelAdmin(ModelBase):  
    class GenreInLine(GenreModelBase):
        model = artikel.genre.through
        extra = 1
    class SchlInLine(SchlagwortModelBase):
        model = artikel.schlagwort.through
        extra = 1
    class PersonInLine(TabModelBase):
        model = artikel.person.through
        verbose_model = person
    class AutorInLine(TabModelBase):
        model = artikel.autor.through
        verbose_model = autor
    class MusikerInLine(TabModelBase):
        model = artikel.musiker.through
        verbose_model = musiker
    class BandInLine(TabModelBase):
        model = artikel.band.through
        verbose_model = band
    class OrtInLine(TabModelBase):
        model = artikel.ort.through
        verbose_model = ort
    class SpielortInLine(TabModelBase):
        model = artikel.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = artikel.veranstaltung.through
        verbose_model = veranstaltung
    inlines = [AutorInLine, SchlInLine, MusikerInLine, BandInLine, GenreInLine, OrtInLine, SpielortInLine, VeranstaltungInLine, PersonInLine]
    flds_to_group = [('ausgabe','magazin', 1),('seite', 'seitenumfang'),]
    
    list_display = ['__str__', 'seite', 'schlagwort_string','ausgabe','artikel_magazin']
    list_filter = [('ausgabe__magazin__magazin_name', DropdownFilter), ('ausgabe__ausgabe_jahr__jahr',DropdownFilter)]
    list_display_links = ['__str__', 'seite']
    search_fields_redirect = {  'ausgabe' : ausgabe.strquery, 
                                'autor' : autor.strquery, 
                                'magazin' : 'ausgabe__magazin__magazin_name',
                                'genre' : ['genre', 'musiker__genre', 'band__genre']
                                }
                                
    advanced_search_form = {
        'gtelt':['seite', ], 
        'selects':['ausgabe__magazin', 'ausgabe', 'schlagwort', 'genre'], 
        'simple':[], 
    }  

    def get_queryset(self, request):
        from django.db.models import Min
        qs = super(ArtikelAdmin, self).get_queryset(request)
        qs = qs.annotate(
                jahre = Min('ausgabe__ausgabe_jahr__jahr'), 
                nums = Min('ausgabe__ausgabe_num__num'), 
                lnums = Min('ausgabe__ausgabe_lnum__lnum'), 
                monate = Min('ausgabe__ausgabe_monat__monat_id'), 
                ).order_by('ausgabe__magazin__magazin_name', 'jahre', 'nums', 'lnums', 'monate', 'seite')
        return qs
        
    def get_changeform_initial_data(self, request):
        initial = super(ArtikelAdmin, self).get_changeform_initial_data(request)
        if '_changelist_filters' not in initial.keys():
            return initial
        filter_dict = initial['_changelist_filters']
        if 'magazin' in filter_dict.keys() or 'ausgabe__magazin__magazin_name' in filter_dict.keys():
            if 'ausgabe__magazin__magazin_name' in filter_dict.keys():
                v = filter_dict['ausgabe__magazin__magazin_name']
            else:
                v = filter_dict['magazin']
            try:
                v = magazin.objects.get(magazin_name=v)
            except:
                return initial
            else:
                initial['magazin'] = v
        if 'ausgabe' in filter_dict.keys() and 'magazin' in initial.keys() and initial['magazin']:
            v = filter_dict['ausgabe']
            mag = initial['magazin']
            qs = ausgabe.strquery_as_queryset(search_term = v, queryset = ausgabe.objects.filter(magazin=mag))
            if qs.count()==1:
                initial['ausgabe'] = qs[0]
        return initial
                

@admin.register(band)    
class BandAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = band.genre.through
    class MusikerInLine(TabModelBase):
        model = band.musiker.through
        verbose_model = musiker
    class AliasInLine(AliasTabBase):
        model = band_alias
    inlines=[GenreInLine, AliasInLine, MusikerInLine]
    exclude = ['genre', 'musiker']
    
    list_display = ['band_name', 'genre_string','herkunft', 'musiker_string']
    list_filter = [('genre__genre', DropdownFilter), ('herkunft__land', RelatedOnlyDropdownFilter)]

    crosslinks = [(artikel, 'band'), (veranstaltung, 'band')]
    googlebtns = ['band_name']
@admin.register(bildmaterial)
class BildmaterialAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    pass
    
@admin.register(buch)
class BuchAdmin(ModelBase):
    class AutorInLine(TabModelBase):
        model = buch.autor.through
        verbose_model = autor
    class BestandInLine(BestandModelBase):
        pass
    inlines = [AutorInLine, BestandInLine]
    flds_to_group = [('jahr', 'verlag'), ('jahr_orig','verlag_orig'), ('EAN', 'ISBN'), ('sprache', 'sprache_orig')]
    exclude = ['autor']
    
@admin.register(dokument)
class DokumentAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    infields = [BestandInLine]
    
@admin.register(genre)
class GenreAdmin(ModelBase):
    class AliasInLine(AliasTabBase):
        model = genre_alias
    inlines = [AliasInLine]
    search_fields = ['genre', 'ober_id__genre', 'genre_alias__alias']
    list_display = ['genre', 'alias_string']
    crosslinks = [(musiker, 'genre'), (band, 'genre'), (artikel, 'genre'), (veranstaltung, 'genre'), (magazin, 'genre')]
    

@admin.register(magazin)
class MagazinAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = magazin.genre.through
        magazin.genre.through.verbose_name = ''
    inlines = [GenreInLine]
    exclude = ['genre']
    
    list_display = ('__str__','beschreibung','anz_ausgaben', 'ort')
    list_filter = [('ort__land', RelatedOnlyDropdownFilter), ]
    

@admin.register(memorabilien)
class MemoAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    infields = [BestandInLine]

@admin.register(musiker)
class MusikerAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = musiker.genre.through
    class BandInLine(TabModelBase):
        model = band.musiker.through
        verbose_name_plural = 'Ist Mitglied in'
        verbose_name = 'Band'
    class AliasInLine(AliasTabBase):
        model = musiker_alias
    class InstrInLine(TabModelBase):
        model = musiker.instrument.through
        verbose_name_plural = 'Spielt Instrument'
        verbose_name = 'Instrument'
    inlines = [AliasInLine, GenreInLine, BandInLine, InstrInLine]
    exclude = ('ist_mitglied', 'instrument', 'genre')
    
    list_display = ['kuenstler_name', 'genre_string', 'band_string']
    search_fields = ['kuenstler_name', 'genre__genre', 'band__band_name']
    
    #advanced_search_form = {'selects':['band']}
    crosslinks = [(artikel, 'musiker')]
    googlebtns = ['kuenstler_name']
    
@admin.register(person)
class PersonAdmin(ModelBase):
    def Ist_Musiker(self, obj):
        return obj.musiker_set.exists()
    Ist_Musiker.boolean = True
    
    def Ist_Autor(self, obj):
        return obj.autor_set.exists()
    Ist_Autor.boolean = True
    
    list_display = ('vorname', 'nachname', 'Ist_Musiker', 'Ist_Autor')
    list_display_links =['vorname','nachname']
    readonly_fields = ['autoren_string', 'musiker_string']
    fields = ['vorname', 'nachname', 'herkunft', 'beschreibung','autoren_string', 'musiker_string']
    
@admin.register(schlagwort)
class SchlagwortTab(ModelBase):
    class AliasInLine(AliasTabBase):
        model = schlagwort_alias
        extra = 1
    inlines = [AliasInLine]
    search_fields = ['schlagwort', 'ober_id__schlagwort', 'schlagwort_alias__alias']
    
@admin.register(spielort)
class SpielortAdmin(ModelBase):
    pass
    
@admin.register(technik)
class TechnikAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    infields = [BestandInLine]

@admin.register(veranstaltung)
class VeranstaltungAdmin(ModelBase):
    pass
#    class GenreInLine(GenreModelBase):
#        model = veranstaltung.genre.through
#    class BandInLine(TabModelBase):
#        model = veranstaltung.band.through
#        verbose_model = band
#    class PersonInLine(TabModelBase):
#        model = veranstaltung.person.through
#        verbose_model = person
#    inlines=[GenreInLine, BandInLine, PersonInLine]
#    exclude = ['genre', 'band', 'person']
    
@admin.register(verlag)
class VerlagAdmin(ModelBase):
    def magazine(self, obj):
        return ", ".join([i.magazin_name for i in obj.magazin_set.all()])
        
    readonly_fields = ['magazine']
    search_fields = ['verlag_name', 'sitz__land__land_name', 'sitz__stadt']
        
@admin.register(video)
class VideoAdmin(ModelBase):
    class BestandInLine(BestandModelBase):
        pass
    infields = [BestandInLine]
        
# ======================================================== Orte ========================================================

@admin.register(bundesland)
class BlandAdmin(ModelBase):
    search_fields = ['id', 'bland_name', 'code', 'land__land_name']
    list_display = ['bland_name', 'code', 'land']
    list_filter = [('land', RelatedOnlyDropdownFilter)]
    
@admin.register(land)
class LandAdmin(ModelBase):
    search_fields = ['id', 'land_name', 'code']
    
@admin.register(kreis)
class KreisAdmin(ModelBase):
    pass
    
@admin.register(ort)
class OrtAdmin(ModelBase):
    fields = ['stadt', 'land', 'bland']
    
    search_fields = ['stadt', 'land__land_name', 'bland__bland_name']
    list_display = ['stadt', 'bland', 'land']
    list_filter = [('land', RelatedDropdownFilter), ('bland', RelatedDropdownFilter)]
    list_display_links = list_display

@admin.register(bestand)
class BestandAdmin(ModelBase):
    pass
    
@admin.register(provenienz)
class ProvAdmin(ModelBase):   
    pass
    #list_display= ['geber', 'typ']
    
# Register your models here.
admin.site.register([buch_serie, monat, instrument, lagerort, geber, sender, sprache,  ])

#admin.site.register(monat)
