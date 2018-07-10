
from django.db.models import Q
from django.utils.translation import gettext
from django.contrib.admin.utils import get_fields_from_path

from dal import autocomplete

from DBentry.models import *
from DBentry.logging import LoggingMixin
from DBentry.utils import get_model_from_string

from django import http

#TODO: review the whole caching thing

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
        #TODO: accurate excepts
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
        qs = self.model.objects.all() if self.queryset is None else self.queryset #TODO: MultipleObjectMixin.get_queryset ?
        
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
    create_field = None

    def dispatch(self, *args, **kwargs):
        if not self.model:
            model_name = kwargs.pop('model_name', '')
            self.model = get_model_from_string(model_name)
        self.create_field = self.create_field or kwargs.pop('create_field', None)
        return super().dispatch(*args, **kwargs)
        
    def get_queryset(self):
        model_name = self.model._meta.model_name
        cache = self.request.session.get('ac-cache', {})
#        if self.q in cache.get(model_name, {}):
#            return cache[model_name][self.q]
        qs = super().get_queryset()
#        if self.q:
#            if not cache or model_name not in cache:
#                self.request.session['ac-cache'] = {model_name:{self.q:qs}}
#            elif model_name in cache:
#                cached = self.request.session['ac-cache'][model_name]
#                cached[self.q] = qs
#                self.request.session['ac-cache'] = {model_name:cached}
        return qs
    
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
        
class ACBuchband(ACBase):
    model = buch
    queryset = buch.objects.filter(is_buchband=True)
    
from .creator import Creator
creation_failed_response = http.JsonResponse({'id':0, 'text':'Creation failed, please use button!'})

class ACCreateable(ACCapture):
    #TODO: handle MultipleObjectsReturnedException raised by creator
    def dispatch(self, *args, **kwargs):
        if not self.model:
            model_name = kwargs.pop('model_name', '')
            self.model = get_model_from_string(model_name)
        self.creator = Creator(self.model)
        self.create_field = self.create_field or kwargs.pop('create_field', None)
        return super().dispatch(*args, **kwargs)
        
    def createable(self, text, creator = None):
        creator = creator or self.creator
        return creator.createable(text)
    
    def get_create_option(self, context, q):
        """Form the correct create_option to append to results."""
        # Override:
        # - to include a hook has_create_field() instead of just checking for if self.create_field (needed for ACProv)
        # - to translate the create text
        create_option = []
        display_create_option = False
        if q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or not self.has_more(context):#or page_obj.number == 1:
                # See if we can create an object from q
                if self.createable(q):
                    display_create_option = True

        if display_create_option and self.has_add_permission(self.request):
            create_option = [{
                'id': q,
                'text': gettext('Create "%(new_value)s"') % {'new_value': q}, 
                'create_id': True,
            }]
            create_info = self.get_creation_info(q)
            if create_info:
                create_option.extend(self.get_creation_info(q))
        
        return create_option
        
    def get_creation_info(self, text, creator = None):
        creator = creator or self.creator
        create_info = []
        default = {'id':None, 'create_id':True, 'text':'...mit folgenden Daten:'} # 'id' : None will make the option unselectable
        
        create_info.append(default.copy())
        for k, v in creator.create_info(text).items():
            if not v or k == 'instance':
                continue
            if isinstance(v, dict):
                for _k, _v in v.items():
                    if not _v or _k == 'instance':
                        continue
                    default['text'] = ' '*4 + str(_k) + ': ' + str(_v)
                    create_info.append(default.copy())
            else:
                default['text'] = str(k) + ': ' + str(v)
                create_info.append(default.copy())
        return create_info
        
    def create_object(self, text, creator = None):
        if self.has_create_field():
            return super().create_object(text)
        creator = creator or self.creator
        created_instance = creator.create(text).get('instance')
        return created_instance

    def post(self, request):
        """Create an object given a text after checking permissions."""
        if not self.has_add_permission(request):
            return http.HttpResponseForbidden()
            
        if not self.creator and not self.create_field:
            raise AttributeError('Missing "create_field"') #TODO: adjust error message

        text = request.POST.get('text', None)

        if text is None:
            return http.HttpResponseBadRequest()

        result = self.create_object(text)

        return http.JsonResponse({
            'id': result.pk,
            'text': six.text_type(result),
        })
