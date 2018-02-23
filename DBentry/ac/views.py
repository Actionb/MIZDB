
from django.db.models import Q
from django.utils.translation import gettext
from django.contrib.admin.utils import get_fields_from_path

from dal import autocomplete

from DBentry.models import *
from DBentry.logging import LoggingMixin
# Create your views here    

# AUTOCOMPLETE VIEWS
class ACBase(autocomplete.Select2QuerySetView, LoggingMixin):
    _flds = None
    
    def has_create_field(self):
        if self.create_field:
            return True
        return False
    
    def get_create_option(self, context, q):
        """Form the correct create_option to append to results."""
        # Override:
        # - to include a hook has_create_field() instead of just checking for if self.create_field (needed for ACProv)
        # - to translate the create text
        create_option = []
        display_create_option = False
        if self.has_create_field() and q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):#or page_obj.number == 1:
                display_create_option = True

        if display_create_option and self.has_add_permission(self.request):
            create_option = [{
                'id': q,
                'text': gettext('Create "%(new_value)s"') % {'new_value': q},
                'create_id': True,
            }]
        return create_option
        
    @property
    def flds(self):
        if not self._flds:
            self._flds = self.model.get_search_fields()
        return self._flds
        
    def do_ordering(self, qs):
        return qs.order_by(*self.model._meta.ordering)
        
    def apply_q(self, qs):
        # NOTE: distinct() at every step? performance issue?
        if self.q:
            if self.flds:
                exact_match_qs = qs
                startsw_qs = qs
                
                try:
                    qobjects = Q()
                    for fld in self.flds:
                        qobjects |= Q((fld, self.q))
                    exact_match_qs = qs.filter(qobjects).distinct()
                except:
                    # invalid lookup/ValidationError (for date fields)
                    exact_match_qs = qs.none()
                    
                try:
                    # __istartswith might be invalid lookup! --> then what about icontains?
                    qobjects = Q()
                    for fld in self.flds:
                        qobjects |= Q((fld+'__istartswith', self.q))
                    startsw_qs = qs.exclude(pk__in=exact_match_qs).filter(qobjects).distinct()
                except:
                    startsw_qs = qs.none()
                    
                # should we even split at spaces? Yes we should! Names for example:
                # searching surname, prename should return results of format prename, surname!
                for q in self.q.split():
                    qobjects = Q()
                    for fld in self.flds:
                        qobjects |= Q((fld+"__icontains", q))
                    qs = qs.exclude(pk__in=startsw_qs).exclude(pk__in=exact_match_qs).filter(qobjects).distinct()
                return list(exact_match_qs)+list(startsw_qs)+list(qs)
        else:
            #TODO: move this into a subclass
            # Fetch favorites if available
            try:
                fav_config = Favoriten.objects.get(user=self.request.user)
            except:
                return qs
            qs = list(fav_config.get_favorites(self.model)) + list(qs)
        return qs
        
    def create_object(self, text):
        """Create an object given a text."""
        # TODO: allow an **expression to create the object (ACProv) // let create_field be an expression?
        object = self.model.objects.create(**{self.create_field: text})
        if object and self.request:
            self.log_addition(object)
        return object
        
    def get_queryset(self):
        qs = self.model.objects.all()
        #ordering = self.model._meta.ordering
        
        if self.forwarded:
            qobjects = Q()
            for k, v in self.forwarded.items():
                #TODO: make a custom widget to allow setting of its 'name' html attribute so we don't have to do this:
                # html attribute name == form field name; meaning in order to use dal in search forms we have to call the
                # form field after a queryable field. But the ac widget's model fields may be different than the form fields
                # 
                while True:
                    # Reducing k in hopes of getting something useful
                    if k:
                        try:
                            # Test to see if k can be used to build a query
                            get_fields_from_path(self.model, k)
                            break
                        except:
                            # Slice off the first bit
                            k = "__".join(k.split("__")[1:])
                    else:
                        break
                if k and v:
                    qobjects |= Q((k,v))
            if qobjects.children:
                qs = qs.filter(qobjects)                        
            else:
                # Return empty queryset as the forwarded items did not contribute to filtering the queryset
                return self.model.objects.none()
        qs = self.do_ordering(qs)
        qs = self.apply_q(qs)
        return qs
    
    def has_add_permission(self, request):
        # Overwritten since get_queryset() may return a list (of exact matches, startswith matches and contains matches) now too.
        # Plus, autocomplete views have a model attribute anyhow. This avoids doing anything expensive in get_queryset.
        """Return True if the user has the permission to add a model."""
        if not request.user.is_authenticated():
            return False
        
        #opts = self.get_queryset().model._meta <--- Overwritten
        from django.contrib.auth import get_permission_codename
        opts = self.model._meta
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))
    
    def get_result_value(self, result):
        """Return the value of a result."""
        if isinstance(result, (list, tuple)):
            return result[0]
        return str(result.pk)

    def get_result_label(self, result):
        """Return the label of a result."""
        if isinstance(result, (list, tuple)):
            return result[1]
        return str(result)
        
class ACProv(ACBase):
    
    model = provenienz
    
    def has_create_field(self):
        return True
        
    def create_object(self, text):
        object = provenienz.objects.create(geber=geber.objects.create(name=text))
        if object and self.request:
            self.log_addition(object)
        return object
        
class ACAusgabe(ACBase):
    
    model = ausgabe
    
    def do_ordering(self, qs):
        return qs.resultbased_ordering()
        
class ACPrototype(ACBase):
    
    model = None
    primary = []
    suffix = {}
    exact_match = False
    _search_fields = []
    
    def get_create_option(self, context, q):
        if self.exact_match:
            # Don't show a create option when an exact match has been found.
            return []
        return super().get_create_option(context, q)
    
    def append_suffix(self, tuple_list, field, lookup=''):
        if field + lookup in self.suffix:
            return [
                (pk, name + " ({})".format(self.suffix.get(field + lookup))) for pk, name in tuple_list
            ]
        elif field in self.suffix:
            return [
                (pk, name + " ({})".format(self.suffix.get(field))) for pk, name in tuple_list
            ]
        else:
            return tuple_list
    
    @property
    def search_fields(self):
        if not self._search_fields:
            self._search_fields = [fld for fld in self.model.get_search_fields() if fld not in self.primary]
        return self._search_fields
        
    def get_namefield(self):
        if hasattr(self, 'name_field') and self.name_field:
            return self.name_field
        if self.primary and self.primary[0]:
            return self.primary[0]
        raise AttributeError("No name_field declared.")
        
    def apply_q(self, qs):
        print("View: Searching...")
        qs = qs.values_list('pk', self.get_namefield())
        rslt = []
        ids_found = set()
        
        for search_field in self.primary:
            search_results = qs.exclude(pk__in=ids_found).filter(**{search_field + '__iexact':self.q})
            rslt.extend(self.append_suffix(search_results, search_field, '__iexact'))
            ids_found.update(search_results.values_list('pk', flat=True))
        self.exact_match = bool(ids_found)
                    
        for search_field in self.primary:
            for lookup in ('__istartswith', '__icontains'):
                search_results = qs.exclude(pk__in=ids_found).filter(**{search_field + lookup:self.q})
                rslt.extend(self.append_suffix(search_results, search_field, lookup))
                ids_found.update(search_results.values_list('pk', flat=True))
        
        for search_field in self.search_fields:
            for lookup in ('__iexact', '__istartswith'):
                search_results = qs.exclude(pk__in=ids_found).filter(**{search_field + lookup:self.q})
                rslt.extend(self.append_suffix(search_results, search_field, lookup))
                ids_found.update(search_results.values_list('pk', flat=True))
                
        weak_hits = []
        
        for search_field in self.search_fields:
            search_results = qs.exclude(pk__in=ids_found).filter(**{search_field + '__icontains':self.q})
            weak_hits.extend(self.append_suffix(search_results, search_field, '__icontains'))
            ids_found.update(search_results.values_list('pk', flat=True))
        if weak_hits:
            #rslt.append((0, '--- schwache Treffer für "{}" ---'.format(self.q)))
            rslt.append((0, '1234567890'*4))
            rslt.extend(weak_hits)
        return rslt
      
    
class ACAusgabe2(ACPrototype):
    #TODO: VDStrat this
    
    model = ausgabe
    primary = ['_name']
    suffix = {
        'ausgabe_monat__monat__monat':'Monat', 
        'sonderausgabe':'Sonderausgabe', 
        'ausgabe_lnum__lnum':'Lnum', 
        'e_datum':'E.datum', 
        'status':'Status', 
        'ausgabe_num__num':'Num', 
        'jahrgang':'Jahrgang', 
        'ausgabe_monat__monat__abk':'Monat Abk.', 
        'ausgabe_jahr__jahr' : 'Jahr'
        }
        
class ACVDStrat(ACPrototype):
    
    model = band
    primary = ['band_name', 'band_alias__alias']
    suffix = {'band_alias__alias':'Band-Alias', 'musiker__kuenstler_name':'Band-Mitglied', 'musiker__musiker_alias__alias':'Mitglied-Alias'}
    
    def apply_q(self, qs):
        from DBentry.query import VDStrat
        strat = VDStrat(qs, self.q, name_field='band_name', primary_fields = self.primary)
        strat.suffix = self.suffix.copy()
        rslt, self.exact_match = strat.search()
        return rslt
