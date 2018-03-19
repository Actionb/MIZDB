
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
        object = self.model.objects.create(**{self.create_field: text})
        if object and self.request:
            self.log_addition(object)
        return object
        
    def get_queryset(self):
        qs = self.model.objects.all()
        
        if self.forwarded:
            if any(k and v for k, v in self.forwarded.items()):
                qobjects = Q()
                for k, v in self.forwarded.items():
                    if k and v:
                        qobjects |= Q((k,v))
                qs = qs.filter(qobjects) 
            else:
                # All forwarded values were None, return an empty queryset
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
    
class ACCapture(ACBase):
    
    def dispatch(self, *args, **kwargs):
        model_name = kwargs.pop('model_name', '')
        from DBentry.utils import get_model_from_string
        self.model = get_model_from_string(model_name)
        self.create_field = kwargs.pop('create_field', None)
        return super().dispatch(*args, **kwargs)
    
    def apply_q(self, qs, use_suffix=True):
        if self.q:
            return qs.find(self.q, use_suffix=use_suffix)
        elif self.model in Favoriten.get_favorite_models():
            # add Favoriten to the top of the result queryset if no search term was given.
            try:
                favorites = Favoriten.objects.get(user=self.request.user)
            except Favoriten.DoesNotExist:
                return qs
            # if there are no favorites for the model, an empty queryset will be returned by get_favorites
            return list(favorites.get_favorites(self.model)) + list(qs) 
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
