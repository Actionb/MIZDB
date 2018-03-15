
from django.db.models import Q
from django.utils.translation import gettext
from django.contrib.admin.utils import get_fields_from_path

from dal import autocomplete

from DBentry.models import *
from DBentry.logging import LoggingMixin
# Create your views here    

# AUTOCOMPLETE VIEWS
class ACBase(autocomplete.Select2QuerySetView, LoggingMixin):
    _search_fields = None
    
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
    def search_fields(self):
        if not self._search_fields:
            self._search_fields = self.model.get_search_fields()
        return self._search_fields
                
    def do_ordering(self, qs):
        return qs.order_by(*self.model._meta.ordering)
        
    def apply_q(self, qs):
        # NOTE: distinct() at every step? performance issue?
        if self.q:
            if self.search_fields:
                exact_match_qs = qs
                startsw_qs = qs
                
                try:
                    qobjects = Q()
                    for fld in self.search_fields:
                        qobjects |= Q((fld, self.q))
                    exact_match_qs = qs.filter(qobjects).distinct()
                except:
                    # invalid lookup/ValidationError (for date fields)
                    exact_match_qs = qs.none()
                    
                try:
                    # __istartswith might be invalid lookup! --> then what about icontains?
                    qobjects = Q()
                    for fld in self.search_fields:
                        qobjects |= Q((fld+'__istartswith', self.q))
                    startsw_qs = qs.exclude(pk__in=exact_match_qs).filter(qobjects).distinct()
                except:
                    startsw_qs = qs.none()
                    
                # should we even split at spaces? Yes we should! Names for example:
                # searching surname, prename should return results of format prename, surname!
                for q in self.q.split():
                    qobjects = Q()
                    for fld in self.search_fields:
                        qobjects |= Q((fld+"__icontains", q))
                    qs = qs.exclude(pk__in=startsw_qs).exclude(pk__in=exact_match_qs).filter(qobjects).distinct()
                return list(exact_match_qs)+list(startsw_qs)+list(qs)
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
                # form field after a queryable field. But the ac widget's model fields may be different from the form fields
                # 
                # NOTE: use a partial dal.forward.Field: 
                # pf = partial(forward.Field,dst='magazin')
                # widget.forward = [pf(src='whatever_field_name')]

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
        
class ACVDStrat(ACBase):
    
    exact_match = False
    
    def get_create_option(self, context, q):
        if self.exact_match:
            # Don't show a create option when an exact match has been found.
            return []
        return super().get_create_option(context, q)
    
    def apply_q(self, qs):
        from DBentry.query import ValuesDictStrategy
        rslt, self.exact_match = ValuesDictStrategy(qs).search(self.q)
        return rslt
        
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
        
class ACFavoritenMixin(object):
    """
    A mixin that adds Favoriten to the top of the result queryset if no search term was given.
    """
    
    def apply_q(self, qs):
        if self.q:
            qs = super().apply_q(qs)
        else:
            # Fetch favorites if available
            try:
                fav_config = Favoriten.objects.get(user=self.request.user)
            except Favoriten.DoesNotExist:
                return qs
            # if there are no favorites for the model, an empty queryset will be returned by get_favorites
            qs = list(fav_config.get_favorites(self.model)) + list(qs) 
        return qs
        
class ACGenre(ACFavoritenMixin, ACBase):
    model = genre

class ACSchlagwort(ACFavoritenMixin, ACBase):
    model = schlagwort
    
class ACCapture(ACBase):
    
    def dispatch(self, *args, **kwargs):
        model_name = kwargs.pop('model_name', '')
        from DBentry.utils import get_model_from_string
        self.model = get_model_from_string(model_name)
        self.create_field = kwargs.pop('create_field', None)
        return super().dispatch(*args, **kwargs)
    
    def apply_q(self, qs):
        if self.q:
            return qs.find(self.q)
        else:
            return qs
        
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
