
from collections import OrderedDict

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse, resolve
from django.shortcuts import redirect
from django.contrib.auth import get_permission_codename

from .models import *
from .forms import makeForm, InLineAusgabeForm
from .utils import link_list
from .changelist import MIZChangeList
from .actions import *

from .sites import miz_site

MERGE_DENIED_MSG = 'Die ausgewählten {} gehören zu unterschiedlichen {}{}.'


class ModelBase(admin.ModelAdmin):
    
    def __init__(self, *args, **kwargs):
        super(ModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(self.model)
        
    search_fields_redirect = dict()
    flds_to_group = []
    googlebtns = []
    collapse_all = False                    # Whether to collapse all inlines/fieldsets by default or not
    hint = ''                               # A hint displayed at the top of the form 
    actions = [merge_records]

    def has_adv_sf(self):
        return len(getattr(self, 'advanced_search_form', []))>0
    
    def get_changelist(self, request, **kwargs):
        return MIZChangeList
        
    def get_actions(self, request):
        # Show actions based on user permissions
        actions = super(ModelBase, self).get_actions(request) #= OrderedDict( (name, (func, name, desc)) )
        
        #TODO: use ActionConfirmationView + MIZAdminPermissionMixin permission_test() to unify all the things?
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
        
    def get_form(self, request, obj=None, **kwargs):
        # Wrap all the things
        # We cannot do this in the form.__init__ since an add form without initial values never gets initialized - 
        # meaning we do not get any related widget stuff
        form = super(ModelBase, self).get_form(request, obj, **kwargs)
        from DBentry.ac.widgets import wrap_dal_widget
        for fld in form.declared_fields.values():
            widget = fld.widget
            try:
                widget = wrap_dal_widget(fld.widget)
            except:
                continue
            fld.widget = widget
        return form
    
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
        return self.model.get_search_fields()
        
    def add_crosslinks(self, object_id):
        new_extra = {}
        new_extra['crosslinks'] = []
        
        inlmdls = {i.model for i in self.inlines}
        for rel in self.opts.related_objects:
            if rel.many_to_many or rel.one_to_many:
                model = rel.related_model
                fld_name = rel.remote_field.name
                if model in inlmdls:
                    continue
                count = model._default_manager.filter(**{fld_name:object_id}).count()
                if not count:
                    continue
                try:
                    link = reverse("admin:{}_{}_changelist".format(self.opts.app_label, model._meta.model_name)) \
                                    + "?" + fld_name + "=" + str(object_id)
                except Exception as e:
                    # No reverse match found
                    continue
                label = model._meta.verbose_name_plural + " ({})".format(str(count))
                new_extra['crosslinks'].append( dict(link=link, label=label) )
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
        from django.utils.http import unquote
        initial = super(ModelBase, self).get_changeform_initial_data(request)
        if '_changelist_filters' not in initial.keys() or not initial['_changelist_filters']:
            return initial
            
        # At this point, _changelist_filters is a string of format:
        # '_changelist_filters': 'ausgabe__magazin=47&ausgabe=4288'
        # SEARCH_TERM_SEP: '='
        # SEARCH_SEG_SEP: ','
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
        
    def merge_allowed(self, request, queryset):
        """ Hook for checks on merging. """
        #TODO: move this to actions.py
        return True
        
class TabModelBase(admin.TabularInline):
    original = False
    verbose_model = None
    extra = 1
    classes = ['collapse']
    def __init__(self, *args, **kwargs):
        super(TabModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(model = self.model)
        if self.verbose_model:
            self.verbose_name = self.verbose_model._meta.verbose_name
            self.verbose_name_plural = self.verbose_model._meta.verbose_name_plural
            
class StackModelBase(admin.StackedInline):
    original = False
    verbose_model = None
    extra = 1
    classes = ['collapse']
    def __init__(self, *args, **kwargs):
        super(StackModelBase, self).__init__(*args, **kwargs)
        self.form = makeForm(model = self.model)
        if self.verbose_model:
            self.verbose_name = self.verbose_model._meta.verbose_name
            self.verbose_name_plural = self.verbose_model._meta.verbose_name_plural

class AliasTabBase(TabModelBase):
    verbose_name_plural = 'Alias'
    
class BestandInLine(TabModelBase):
    model = bestand
    readonly_fields = ['signatur']
    fields = ['signatur', 'lagerort', 'provenienz']
    verbose_name = bestand._meta.verbose_name
    verbose_name_plural = bestand._meta.verbose_name_plural
    
class GenreModelBase(TabModelBase):
    extra = 1
    verbose_name = genre._meta.verbose_name
    verbose_name_plural = genre._meta.verbose_name_plural
    
class SchlagwortModelBase(TabModelBase):
    extra = 1
    verbose_name = schlagwort._meta.verbose_name
    verbose_name_plural = schlagwort._meta.verbose_name_plural
    
class DateiInLine(TabModelBase):
    model = m2m_datei_quelle
    verbose_model = datei
    fields = ['datei']

class QuelleInLine(StackModelBase):
    extra = 0
    model = m2m_datei_quelle
    description = 'Verweise auf das Herkunfts-Medium (Tonträger, Videoband, etc.) dieser Datei.'
    
class AusgabeInLineBase(admin.TabularInline):
    model = None
    fields = ['magazin', 'ausgabe']
    original = False
    extra = 1
    classes = ['collapse']
    def __init__(self, *args, **kwargs):
        self.form = InLineAusgabeForm
        super(AusgabeInLineBase, self).__init__(*args, **kwargs)
        self.verbose_name = ausgabe._meta.verbose_name
        self.verbose_name_plural = ausgabe._meta.verbose_name_plural
        
        
@admin.register(audio, site=miz_site)
class AudioAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = audio.genre.through
    class SchlInLine(SchlagwortModelBase):
        model = audio.schlagwort.through
    class PersonInLine(TabModelBase):
        model = audio.person.through
        verbose_model = person
    class MusikerInLine(StackModelBase):
        model = audio.musiker.through
        verbose_model = musiker
        extra = 0
        filter_horizontal = ['instrument']
        fieldsets = [
            (None, {'fields' : ['musiker']}), 
            ("Instrumente", {'fields' : ['instrument'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class BandInLine(TabModelBase):
        model = audio.band.through
        verbose_model = band
    class SpielortInLine(TabModelBase):
        model = audio.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = audio.veranstaltung.through
        verbose_model = veranstaltung
    class FormatInLine(StackModelBase):
        model = Format
        extra = 0
        filter_horizontal = ['tag']
        fieldsets = [
            (None, {'fields' : ['anzahl', 'format_typ', 'format_size', 'catalog_nr', 'tape', 'channel', 'noise_red']}), 
            ('Tags', {'fields' : ['tag'], 'classes' : ['collapse', 'collapsed']}), 
            ('Bemerkungen', {'fields' : ['bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class OrtInLine(TabModelBase):
        model = audio.ort.through
        verbose_model = ort
    class PlattenInLine(TabModelBase):
        model = audio.plattenfirma.through
        verbose_model = plattenfirma
    class AusgabeInLine(AusgabeInLineBase):
        model = ausgabe.audio.through
    inlines = [PlattenInLine, FormatInLine, DateiInLine, MusikerInLine, BandInLine, GenreInLine, SchlInLine, 
            VeranstaltungInLine, SpielortInLine, OrtInLine, PersonInLine, BestandInLine, AusgabeInLine]
    fieldsets = [
        (None, {'fields' : ['titel', 'tracks', 'laufzeit', 'e_jahr', 'quelle', 'sender']}), 
        ('Discogs', {'fields' : ['release_id', 'discogs_url'], 'classes' : ['collapse', 'collapsed']}), 
        ('Bemerkungen', {'fields' : ['bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
    ]
    list_display = ['__str__', 'formate_string', 'kuenstler_string']
    save_on_top = True
    collapse_all = True
    
    advanced_search_form = {
        'selects' : ['musiker', 'band', 'genre', 'spielort', 'veranstaltung', 'plattenfirma', 
                        'format__format_size', 'format__format_typ', 'format__tag'], 
        'simple' : ['release_id'], 
        'labels' : {'format__tag':'Tags'}, 
    }
    
    
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

@admin.register(ausgabe, site=miz_site)
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
    class AudioInLine(TabModelBase):
        model = ausgabe.audio.through
    inlines = [NumInLine,  MonatInLine, LNumInLine, JahrInLine,BestandInLine, AudioInLine]
    flds_to_group = [('status', 'sonderausgabe')]
    
    list_display = ('__str__', 'num_string', 'lnum_string','monat_string','jahre', 'jahrgang', 
                        'magazin','e_datum','anz_artikel', 'status') 
    search_fields = ['magazin__magazin_name', 'status', 'e_datum', 
        'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr','ausgabe_monat__monat__monat']
    search_fields_redirect = { 
                            'bearbeitungsstatus' : 'status',
                            'nr' : 'ausgabe_num__num', 
                            'nummer' : 'ausgabe_num__num', 
                            'lfd' : 'ausgabe_lnum__lnum', 
                            }
                            
    actions = [bulk_jg, add_bestand]
    advanced_search_form = {
        'gtelt':['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum'], 
        'selects':['magazin','status'], 
        'simple':['jahrgang', 'sonderausgabe']
    }
       
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
    add_duplicate.perm_required = ['alter_bestand']
    
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
    add_duplicate.perm_required = ['alter_bestand']
        

        
    def merge_allowed(self, request, queryset):
        #TODO: move this to actions.py
        #TODO: allow merging of non-sonderausgaben with sonderausgaben?
        if queryset.values_list('magazin').distinct().count()>1:
            # User is trying to merge ausgaben from different magazines
            self.message_user(request, MERGE_DENIED_MSG.format(self.opts.verbose_name_plural, magazin._meta.verbose_name_plural, 'n'), 'error')
            return False
        return True
    
@admin.register(autor, site=miz_site)
class AutorAdmin(ModelBase):
    class MagazinInLine(TabModelBase):
        model = autor.magazin.through
        extra = 1
    
    inlines = [MagazinInLine]
    
    list_display = ['__str__', 'magazin_string']
    search_fields = ['person__vorname', 'person__nachname', 'kuerzel']
    search_fields_redirect = {'vorname':'person__vorname', 'nachname':'person__nachname'}

    advanced_search_form = {
        'selects' : ['magazin']
    }
    
@admin.register(artikel, site=miz_site)
class ArtikelAdmin(ModelBase):  
    class GenreInLine(GenreModelBase):
        model = artikel.genre.through
    class SchlInLine(SchlagwortModelBase):
        model = artikel.schlagwort.through
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
    
    list_display = ['__str__', 'zusammenfassung_string', 'seite', 'schlagwort_string','ausgabe','artikel_magazin', 'kuenstler_string']
    list_display_links = ['__str__', 'seite']
    search_fields_redirect = { 
                                'magazin' : 'ausgabe__magazin__magazin_name',
                                'genre' : ['genre', 'musiker__genre', 'band__genre']
                                }
                                
    advanced_search_form = {
        'gtelt':['seite', ], 
        'selects':['ausgabe__magazin', 'ausgabe', 'schlagwort', 'genre', 'band', 'musiker', 'autor'], 
        'simple':[], 
    }  
    save_on_top = True
    #actions = ['merge_records']

    def get_queryset(self, request):
        from django.db.models import Min
        qs = super(ArtikelAdmin, self).get_queryset(request)
        qs = qs.annotate(
                jahre = Min('ausgabe__ausgabe_jahr__jahr'), 
                nums = Min('ausgabe__ausgabe_num__num'), 
                lnums = Min('ausgabe__ausgabe_lnum__lnum'), 
                monate = Min('ausgabe__ausgabe_monat__monat_id'), 
                ).order_by('ausgabe__magazin__magazin_name', 'jahre', 'nums', 'lnums', 'monate', 'seite', 'pk')
        return qs
        
    def merge_allowed(self, request, queryset):
        #TODO: move this to actions.py
        if queryset.values('ausgabe').distinct().count()>1:
            # User is trying to merge artikel from different ausgaben
            self.message_user(request, MERGE_DENIED_MSG.format(self.opts.verbose_name_plural, ausgabe._meta.verbose_name_plural, ''), 'error')
            return False
        return True
        
@admin.register(band, site=miz_site)    
class BandAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = band.genre.through
    class MusikerInLine(TabModelBase):
        model = band.musiker.through
        #verbose_model = musiker
    class AliasInLine(AliasTabBase):
        model = band_alias
    #search_fields = ['band_name', 'beschreibung', 'band_alias__alias']
    save_on_top = True
    inlines=[GenreInLine, AliasInLine, MusikerInLine]
    exclude = ['genre', 'musiker']
    
    list_display = ['band_name', 'genre_string','herkunft', 'musiker_string']

    googlebtns = ['band_name']
    
    advanced_search_form = {
        'selects' : ['musiker', 'genre', 'herkunft__land', 'herkunft'], 
        'labels' : {'musiker':'Mitglied','herkunft__land':'Herkunftsland', 'herkunft':'Herkunftsort'}
    }
    
@admin.register(bildmaterial, site=miz_site)
class BildmaterialAdmin(ModelBase):
    pass
    
@admin.register(buch, site=miz_site)
class BuchAdmin(ModelBase):
    class AutorInLine(TabModelBase):
        model = buch.autor.through
        verbose_model = autor
    save_on_top = True
    inlines = [AutorInLine, BestandInLine]
    flds_to_group = [('jahr', 'verlag'), ('jahr_orig','verlag_orig'), ('EAN', 'ISBN'), ('sprache', 'sprache_orig')]
    exclude = ['autor']
    
@admin.register(dokument, site=miz_site)
class DokumentAdmin(ModelBase):
    infields = [BestandInLine]
    
@admin.register(genre, site=miz_site)
class GenreAdmin(ModelBase):
    class AliasInLine(AliasTabBase):
        model = genre_alias
    inlines = [AliasInLine]
    list_display = ['genre', 'alias_string', 'ober_string']
    
    #TODO: dont keep this
    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            # dont do this crap without a search term, django will explode
            return super(GenreAdmin, self).get_search_results(request, queryset, search_term)
        pre_result, use_distinct = super(GenreAdmin, self).get_search_results(request, queryset, search_term)
        
        q = models.Q()
        for r in pre_result:
            q |= models.Q(('obergenre__genre', r.genre))
            q |= models.Q(('pk', r.pk))
        return queryset.filter(q), use_distinct

@admin.register(magazin, site=miz_site)
class MagazinAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = magazin.genre.through
        magazin.genre.through.verbose_name = ''
    inlines = [GenreInLine]
    exclude = ['genre']
    
    list_display = ('__str__','beschreibung','anz_ausgaben', 'ort')
    
    advanced_search_form = {
        'selects' : ['ort__land'], 
        'labels' : {'ort__land':'Herausgabeland'}
    }
    

@admin.register(memorabilien, site=miz_site)
class MemoAdmin(ModelBase):
    infields = [BestandInLine]

@admin.register(musiker, site=miz_site)
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
    save_on_top = True
    inlines = [AliasInLine, GenreInLine, BandInLine, InstrInLine]
    readonly_fields = ['herkunft_string']
    fields = ['kuenstler_name', ('person', 'herkunft_string'), 'beschreibung']
    exclude = ('ist_mitglied', 'instrument', 'genre')
    
    list_display = ['kuenstler_name', 'genre_string', 'band_string', 'herkunft_string']
    search_fields = ['kuenstler_name', 'musiker_alias__alias']
    
    googlebtns = ['kuenstler_name']
    
    advanced_search_form = {
        'selects' : ['person', 'genre', 'band', 
                'instrument','person__herkunft__land', 'person__herkunft'], 
        'labels' : {'person__herkunft__land':'Herkunftsland'}
    }
    
@admin.register(person, site=miz_site)
class PersonAdmin(ModelBase):
    def Ist_Musiker(self, obj):
        return obj.musiker_set.exists()
    Ist_Musiker.boolean = True
    
    def Ist_Autor(self, obj):
        return obj.autor_set.exists()
    Ist_Autor.boolean = True
    
    list_display = ('vorname', 'nachname', 'Ist_Musiker', 'Ist_Autor')
    list_display_links =['vorname','nachname']
    fields = ['vorname', 'nachname', 'herkunft', 'beschreibung']
    
    advanced_search_form = {
        'selects' : ['herkunft', 'herkunft__land', 'herkunft__bland']
    }
    
@admin.register(schlagwort, site=miz_site)
class SchlagwortAdmin(ModelBase):
    #TODO: rename this class! AHHH!
    class AliasInLine(AliasTabBase):
        model = schlagwort_alias
        extra = 1
    inlines = [AliasInLine]
    list_display = ['schlagwort', 'alias_string', 'ober_string']
    
@admin.register(spielort, site=miz_site)
class SpielortAdmin(ModelBase):
    pass
    
@admin.register(technik, site=miz_site)
class TechnikAdmin(ModelBase):
    infields = [BestandInLine]

@admin.register(veranstaltung, site=miz_site)
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
    
@admin.register(verlag, site=miz_site)
class VerlagAdmin(ModelBase):
    list_display = ['verlag_name', 'sitz']
    search_fields = ['verlag_name', 'sitz__land__land_name', 'sitz__stadt']
    advanced_search_form = {
        'selects' : ['sitz','sitz__land', 'sitz__bland'], 
        'labels' : {'sitz':'Sitz'}
    }
    
        
@admin.register(video, site=miz_site)
class VideoAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = video.genre.through
    class SchlInLine(SchlagwortModelBase):
        model = video.schlagwort.through
    class PersonInLine(TabModelBase):
        model = video.person.through
        verbose_model = person
    class MusikerInLine(TabModelBase):
        model = video.musiker.through
        verbose_model = musiker
    class BandInLine(TabModelBase):
        model = video.band.through
        verbose_model = band
    class SpielortInLine(TabModelBase):
        model = video.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = video.veranstaltung.through
        verbose_model = veranstaltung
    inlines = [BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine, BestandInLine]
        
# ======================================================== Orte ========================================================

@admin.register(bundesland, site=miz_site)
class BlandAdmin(ModelBase):
    search_fields = ['id', 'bland_name', 'code', 'land__land_name']
    list_display = ['bland_name', 'code', 'land']
    advanced_search_form = {
        'selects' : ['ort__land'], 
    }
    
@admin.register(land, site=miz_site)
class LandAdmin(ModelBase):
    search_fields = ['id', 'land_name', 'code']
    
@admin.register(kreis, site=miz_site)
class KreisAdmin(ModelBase):
    pass
    
@admin.register(ort, site=miz_site)
class OrtAdmin(ModelBase):
    fields = ['stadt', 'land', 'bland']
    
    search_fields = ['stadt', 'land__land_name', 'bland__bland_name']
    list_display = ['stadt', 'bland', 'land']
    list_display_links = list_display
    
    advanced_search_form = {
        'selects' : ['land', 'bland']
    }
    
@admin.register(bestand, site=miz_site)
class BestandAdmin(ModelBase):
    #readonly_fields = ['audio', 'ausgabe', 'ausgabe_magazin', 'bildmaterial', 'buch', 'dokument', 'memorabilien', 'technik', 'video']
    list_display = ['signatur', 'bestand_art', 'lagerort','provenienz']
    #flds_to_group = [('ausgabe', 'ausgabe_magazin')]
    
    advanced_search_form = {
        'selects' : ['bestand_art', 'lagerort'], 
    }
    
@admin.register(provenienz, site=miz_site)
class ProvAdmin(ModelBase):   
    pass
      
@admin.register(datei, site=miz_site)
class DateiAdmin(ModelBase):
    class GenreInLine(GenreModelBase):
        model = datei.genre.through
    class SchlInLine(SchlagwortModelBase):
        model = datei.schlagwort.through
    class PersonInLine(TabModelBase):
        model = datei.person.through
        verbose_model = person
    class MusikerInLine(StackModelBase):
        model = datei.musiker.through
        verbose_model = musiker
        filter_horizontal = ['instrument']
    class BandInLine(TabModelBase):
        model = datei.band.through
        verbose_model = band
    class SpielortInLine(TabModelBase):
        model = datei.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(TabModelBase):
        model = datei.veranstaltung.through
        verbose_model = veranstaltung
    inlines = [QuelleInLine, BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine]
    fieldsets = [
        (None, { 'fields': ['titel', 'media_typ', 'datei_pfad', 'provenienz']}),
        ('Allgemeine Beschreibung', { 'fields' : ['beschreibung', 'datum', 'quelle', 'sender', 'bemerkungen']}),  
    ]
    save_on_top = True
    collapse_all = True
    hint = 'Diese Seite ist noch nicht vollständig fertig gestellt. Bitte noch nicht benutzen.'
    
@admin.register(instrument, site=miz_site)
class InstrumentAdmin(ModelBase):
    list_display = ['instrument', 'kuerzel']

# Register your models here.

miz_site.register([buch_serie, monat, lagerort, geber, sender, sprache, plattenfirma])

miz_site.register([Format, FormatTag, FormatSize, FormatTyp, NoiseRed])
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
miz_site.register(Group, GroupAdmin)
miz_site.register(User, UserAdmin)
