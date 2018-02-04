from dal import autocomplete
from DBentry.models import provenienz, ausgabe, geber, Favoriten
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.contrib.admin.utils import get_fields_from_path
# Create your views here

def log_addition(request, object):
    from django.contrib.admin.options import get_content_type_for_model
    from django.contrib.admin.models import LogEntry, ADDITION
    from django.utils.encoding import force_text
    return LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=get_content_type_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_text(object),
        action_flag=ADDITION,
        change_message='[{"added": {}}]',
    )
    

# AUTOCOMPLETE VIEWS
class ACBase(autocomplete.Select2QuerySetView):
    _flds = None
    
    def has_create_field(self):
        if self.create_field:
            return True
        return False
    
    def get_create_option(self, context, q):
        """Form the correct create_option to append to results. IN GERMAN!"""
        #TODO: correctly use the django translation
        create_option = []
        display_create_option = False
        if self.has_create_field() and q:
            page_obj = context.get('page_obj', None)
            if page_obj is None or page_obj.number == 1:
                display_create_option = True

        if display_create_option and self.has_add_permission(self.request):
            create_option = [{
                'id': q,
                'text': _('Erstelle "%(new_value)s"') % {'new_value': q},
                'create_id': True,
            }]
        return create_option
        
    @property
    def flds(self):
        if not self._flds:
            self._flds = self.model.get_search_fields()
            # Check if all flds in self.flds are of the model
            for i, fld in enumerate(self._flds):
                try:
                    flds = get_fields_from_path(self.model, fld)
                except:
                    pass
                else:
                    if flds[0].model == self.model:
                        # All is good, let's continue with the next field
                        continue
                # Either get_fields_from_path threw an error or the field is not of the model
                try:
                    del self._flds[fld]
                except:
                    try:
                        self._flds.remove(i)
                    except:
                        continue
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
            # Fetch favorites if available
            try:
                fav_config = Favoriten.objects.get(user=self.request.user)
            except:
                return qs
            qs = list(fav_config.get_favorites(self.model)) + list(qs)
        return qs
        
    def create_object(self, text):
        """Create an object given a text."""
        object = self.model.objects.create(**{self.create_field: text})
        if object and self.request:
            log_addition(self.request, object)
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
        
class ACProv(ACBase):
    
    model = provenienz
    
    def has_create_field(self):
        return True
        
    def create_object(self, text):
        object = provenienz.objects.create(geber=geber.objects.create(name=text))
        if object and self.request:
            log_addition(self.request, object)
        return object
        
class ACAusgabe(ACBase):
    
    model = ausgabe
    
    def do_ordering(self, qs):
        return qs.resultbased_ordering()
    
    def apply_q(self, qs):
        if self.q:
            if self.forwarded:
                str_dict = {i:i.__str__() for i in qs}
                filtered = [k for k, v in str_dict.items() if self.q in v]
                if filtered:
                    return filtered
            qitems = ausgabe.strquery(self.q)
            if qitems:
                # strquery returned something useful
                for q in qitems:
                    qs = qs.filter(*q)
            else:
                qs = super(ACAusgabe, self).apply_q(qs)
        return qs
                
