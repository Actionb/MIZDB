from collections import OrderedDict

from django.shortcuts import render, redirect
from django.http import HttpResponse

from django.db.models.fields import AutoField, related
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.utils.translation import ugettext as _
from django.contrib.admin.utils import get_fields_from_path

from .models import *
from .forms import *

from dal import autocomplete
# Create your views here

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
            self._flds = self.model.get_primary_fields()
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
                del self._flds[i]
        return self._flds
        
    def get_queryset(self):
        qs = self.model.objects.all()
        ordering = self.model._meta.ordering
                
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
                
        # Ordering
        if self.model == ausgabe:
            qs = qs.resultbased_ordering()
        else:
            qs = qs.order_by(*ordering)
            
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
                    
        return qs
    
    def has_add_permission(self, request):
        # Overwritten since get_queryset() may return a list now too...
        """Return True if the user has the permission to add a model."""
        if not request.user.is_authenticated():
            return False

        #opts = self.get_queryset().model._meta
        from django.contrib.auth import get_permission_codename
        opts = self.model._meta
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))
        
class ACProv(ACBase):
    
    def has_create_field(self):
        return True
        
    def create_object(self, text):
        return provenienz.objects.create(geber=geber.objects.create(name=text))
        
from .admin import admin_site
from django.views.generic import FormView, TemplateView, ListView
class MIZAdminView(FormView):
    form_class = None
    template_name = None
    
    def dispatch(self, request, *args, **kwargs):
        kwargs.update(admin_site.each_context(request))
        return super(MIZAdminView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Default get method of ProcessFormView calls get_context_data withouth kwargs ... for whatever reason
        #NOTE: what did we need this for again? Something to do with site_header, site_titel etc... I think
        return self.render_to_response(self.get_context_data(**kwargs))
        

class BulkBase(MIZAdminView):
    template_name = 'admin/bulk.html'
    form_class = None
    save_redirect = ''
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = self.form_class(request.POST)
        if form.is_valid():
                #TODO: has_changed check to avoid saving the wrong data
            if '_preview' in request.POST: #not self.request.POST.get('preview')
                context['preview_headers'], context['preview'] = self.build_preview(request, form)
            if '_continue' in request.POST:
                # Collect preview data, create instances
                ids = self.save_data(request, form)
                # Need to store the queryset of the newly created items in request.session for the Changelist view...
                request.session['qs'] = dict(id__in=ids) if ids else None
                return redirect(self.save_redirect)
            if '_addanother' in request.POST:
                old_form = form
                form = self.form_class(self.next_initial_data(form))
                form.is_valid()
                context['preview_headers'], context['preview'] = self.build_preview(request, form)
        context['form'] = form
        return render(request, self.template_name, context = context)
    
    def next_initial_data(self, form):
        return form.data
    
    def save_data(self, request, form):
        return []
        
    def build_preview(self, request, form):
        return 
        
    def instance_data(self, row):
        #TODO: this is WIP
        for fld_name in form.each_fields:
            if fld_name in form.split_data:
                continue
                rslt[fld_name] = form.split_data.get(fld_name)
            else:
                rslt[fld_name] = form.cleaned_data.get(fld_name)
        return rslt

class BulkAusgabe(BulkBase):
    form_class = BulkFormAusgabe
    save_redirect = 'MIZAdmin:DBentry_ausgabe_changelist'
    
    def save_data(self, request, form):
        ids = []
        row_count = len(form.row_data)
        
        for row in form.row_data:
            instance = row.get('instance', None) or ausgabe(**self.instance_data(row)) 
            if not instance.pk:
                instance.save()
            for fld_name in ['jahr', 'num', 'monat', 'lnum']:
                set = getattr(instance, "ausgabe_{}_set".format(fld_name))
                data = row.get(fld_name, None)
                if data:
                    if fld_name == 'monat':
                        fld_name = 'monat_id'
                    if isinstance(data, str) or isinstance(data, int):
                        data = [data]
                    for value in data:
                        if value:
                            try:
                                set.create(**{fld_name:value})
                            except Exception as e:
                                # Let something else handle UNIQUE constraints violations
                                #print(e, data)
                                continue
            # Audio
            if 'audio' in row:
                suffix = instance.__str__()
                audio_data = dict(titel = 'Musik-Beilage: {}'.format(str(row.get('magazin')[0])) + " " + suffix, 
                                                    quelle = 'Magazin', 
                                                    e_jahr = row.get('jahr')[0], 
                                                    )
                if audio.objects.filter(**audio_data).exists():
                    audio_instance = audio.objects.filter(**audio_data).first()
                else:
                    audio_instance = audio(**audio_data)
                    audio_instance.save()
                # set.add/ set.create didnt work for some fcking reason
                ergh = m2m_audio_ausgabe(ausgabe=instance, audio=audio_instance)
                ergh.save()
                
            # Bestand
            instance.bestand_set.create(lagerort=row.get('lagerort')[0])
            
            ids.append(instance.pk)
        return ids
                
    def next_initial_data(self, form):
        data = form.data.copy()
        # Increment jahr and jahrgang
        #jahr_list = form.cleaned_data.get('jahr', '').split(', ')
        data['jahr'] = ", ".join([str(int(j)+len(form.row_data[0].get('jahr'))) for j in form.row_data[0].get('jahr')])
        if form.cleaned_data.get('jahrgang'):  
            data['jahrgang'] = form.cleaned_data.get('jahrgang') + 1
        return data
            
    def instance_data(self, row):
        rslt = {}
        rslt['jahrgang'] = row.get('jahrgang', None)
        rslt['magazin'] = row.get('magazin')[0]
        return rslt
        
    def build_preview(self, request, form):
        from django.contrib.admin.utils import reverse
        from django.utils.html import format_html
        preview_data = []
        
        for row in form.row_data:
            preview_row = OrderedDict()
            for fld_name in form.field_order:
                if fld_name == 'audio':
                    if row.get(fld_name):
                        img = format_html('<img alt="True" src="/static/admin/img/icon-yes.svg">')
                    else:
                        img = format_html('<img alt="False" src="/static/admin/img/icon-no.svg">')
                    preview_row[fld_name] = img
                    continue
                values_list = row.get(fld_name) or []
                if len(values_list)==1:
                    preview_row[fld_name] = values_list[0] or ''
                else:
                    preview_row[fld_name] = ", ".join(values_list)
        
            preview_row['Instanz'] = row.get('instance', '') or ''
            if preview_row['Instanz']:
                link = reverse("MIZAdmin:DBentry_ausgabe_change", args = [preview_row['Instanz'].pk])
                label = str(preview_row['Instanz'])
                img = format_html('<img alt="False" src="/static/admin/img/icon-alert.svg">')
                preview_row['Instanz'] = format_html('{} <a href="{}" target="_blank">{}</a>', img, link, label)
            preview_data.append(preview_row)
            
        headers = [
            form.fields.get(fld_name).label or fld_name for fld_name in form.field_order
            ] + ['Bereits vorhanden']
        return headers, preview_data
