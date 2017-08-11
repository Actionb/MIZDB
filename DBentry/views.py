from django.shortcuts import render
from django.http import HttpResponse

from django.db.models.fields import AutoField, related
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.utils.translation import ugettext as _

from .models import *

from dal import autocomplete
# Create your views here


# AUTOCOMPLETE VIEWS
# TODO: rework this, it's a bit derpy and quite old
class ACBase(autocomplete.Select2QuerySetView):
    flds = None
    
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
        
    def get_primary_fields(self):
        return self.flds or self.model.get_primary_fields()
#        #NOTE: check if get_basefields() etc could be used
#        opts = self.model._meta
#        flds = []
#        for fld in opts.get_fields():
#            if fld.name != 'id':
#                if not fld.related_model:   # isinstance(ManyToOne,related.RelatedField) =True, self-linking ober not in opts.related_objects 
#                    flds.append(fld.name)
#                elif include_alias and fld.name.endswith('_alias'):
#                    flds.append(fld.name+'__alias')
#                
#        return flds
        
    def get_queryset(self):
        # TODO: exception fld in self.flds not in self.model._meta.get_fields hä??
        qs = self.model.objects.all()
        ordering = self.model._meta.ordering
        if not self.flds:
            self.flds = self.get_primary_fields()
        if self.forwarded:
            from django.contrib.admin.utils import get_fields_from_path
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
#                if self.forwarded.get(f, 0):   
#                    qobjects |= Q((f, self.forwarded.get(f, 0)))
            if qobjects.children:
                qs = qs.filter(qobjects)                        # NOTE: Oder ver-UND-en? qs.filter().filter()...?
            else:
                return self.model.objects.none()
        if self.q:
            if self.flds:
                # NOTE: should we even split at spaces?
                for q in self.q.split():
                    qobjects = Q()
                    for fld in self.flds:
                        qobjects |= Q((fld+"__icontains", q))
                    qs = qs.filter(qobjects).distinct()
        return qs.order_by(*ordering)
        
class ACProv(ACBase):
    
    def has_create_field(self):
        return True
        
    def create_object(self, text):
        return provenienz.objects.create(geber=geber.objects.create(name=text))
        
class ACList(autocomplete.Select2ListView):
    lst = None
    def get_list(self):
        return self.lst
  
        

