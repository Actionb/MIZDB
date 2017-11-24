from collections import OrderedDict

from django.shortcuts import render, redirect
from django.http import HttpResponse

from django.db.models.fields import AutoField, related
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.utils.translation import ugettext as _
from django.contrib.admin.utils import get_fields_from_path
from django.utils.html import format_html
from django.urls import reverse, resolve

from .models import *
from .utils import link_list
from DBentry.forms import BulkFormAusgabe, FavoritenForm
from .admin import miz_site

from dal import autocomplete
# Create your views here

from django.contrib import admin
from django.contrib import messages
from django.views.generic import FormView, UpdateView

class MIZAdminView(FormView):
    form_class = None
    template_name = None
    
    @classmethod
    def has_permission(cls, request):
        return request.user.is_staff or request.user.is_superuser
    
    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super(MIZAdminView, self).dispatch(request, *args, **kwargs)
    
    
    def get_context_data(self, **kwargs):
        kwargs = super(MIZAdminView, self).get_context_data(**kwargs)
        kwargs.update(miz_site.each_context(self.request))
        return kwargs
        
class FavoritenView(UpdateView):
    form_class = FavoritenForm
    template_name = 'admin/favorites.html'
    model = Favoriten
    
    url_name = 'favoriten'
    index_label = 'Favoriten Verwaltung'
    success_url = ''
    
    @classmethod
    def has_permission(cls, request):
        return request.user.is_staff
        
    def get_context_data(self, **kwargs):
        kwargs = super(FavoritenView, self).get_context_data(**kwargs)
        kwargs.update(miz_site.each_context(self.request))
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super(FavoritenView, self).dispatch(request, *args, **kwargs)
        
    def get_success_url(self):
        # Redirect back onto this site
        return self.success_url
    
    def get_object(self):
        object = Favoriten.objects.filter(user=self.request.user).first()
        if not object:
            object = Favoriten(user=self.request.user)
            object.save()
        return object        
        
class BulkAusgabe(MIZAdminView):
    
    template_name = 'admin/bulk.html'
    form_class = BulkFormAusgabe
    success_url = 'admin:DBentry_ausgabe_changelist'
    url_name = 'bulk_ausgabe'
    index_label = 'Ausgaben Erstellung'
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = self.form_class(request.POST, initial=request.session.get('old_form_data', {}))
        if form.is_valid():
            if form.has_changed() or '_preview' in request.POST:
                if not '_preview' in request.POST:
                    messages.warning(request, 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.')
                context['preview_headers'], context['preview'] = self.build_preview(request, form)
            else:
                if '_continue' in request.POST and not form.has_changed():
                    # Collect preview data, create instances
                    ids, instances = self.save_data(request, form)
                    # Need to store the queryset of the newly created items in request.session for the Changelist view
                    request.session['qs'] = dict(id__in=ids) if ids else None
                    return redirect(self.success_url)
                if '_addanother' in request.POST and not form.has_changed():
                    old_form = form
                    ids, created, updated = self.save_data(request, form)
                    if created:
                        obj_list = link_list(request, created, path = "admin:DBentry_ausgabe_change")
                        messages.success(request, format_html('Ausgaben erstellt: {}'.format(obj_list)))
                    if updated:
                        obj_list = link_list(request, updated, path = "admin:DBentry_ausgabe_change")
                        messages.success(request, format_html('Dubletten hinzugefügt: {}'.format(obj_list)))
                    
                    form = self.form_class(self.next_initial_data(form))
                    form.is_valid()
                    context['preview_headers'], context['preview'] = self.build_preview(request, form)
        request.session['old_form_data'] = form.data
        context['form'] = form
        return render(request, self.template_name, context = context)
    
    def save_data(self, request, form):
        ids = []
        created = []
        updated = []
        
        original = []
        dupes = []
        # Split row_data into rows of duplicates and originals, so we save the originals before any duplicates
        # This assumes row_data does not contain any nested duplicates
        # Also filter out rows that resulted in multiple matching existing instances
        for row in form.row_data:
            if 'multiples' in row:
                continue
            if 'dupe_of' in row:
                dupes.append(row)
            else:
                original.append(row)
                
        from itertools import chain
        
        for row in chain(original, dupes):
            if 'dupe_of' in row:
                instance = row['dupe_of'].get('instance', None)
                if not instance or not instance.pk:
                    # NOTE: can this still happpen?
                    raise ValidationError("Hol mal den Philip!")
                    continue
                bestand_data = dict(lagerort=row.get('lagerort'))
                if 'provenienz' in row['dupe_of']:
                    bestand_data['provenienz'] = row.get('provenienz')
                instance.bestand_set.create(**bestand_data)
                row['instance'] = instance
                updated.append(instance)
                ids.append(instance.pk)
                continue
            
            instance = row.get('instance', None) or ausgabe(**self.instance_data(row)) 
            if not instance.pk:
                instance.save()
                created.append(instance)
            else:
                updated.append(instance)
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
                m2m_instance = m2m_audio_ausgabe(ausgabe=instance, audio=audio_instance)
                m2m_instance.save()
                bestand_data = dict(lagerort=form.cleaned_data.get('audio_lagerort'))
                if 'provenienz' in row:
                    bestand_data['provenienz'] = row.get('provenienz')
                audio_instance.bestand_set.create(**bestand_data)
                
            # Bestand
            bestand_data = dict(lagerort=row.get('lagerort'))
            if 'provenienz' in row:
                bestand_data['provenienz'] = row.get('provenienz')
            instance.bestand_set.create(**bestand_data)
            
            row['instance'] = instance
            ids.append(instance.pk)
        return ids, created, updated
                
    def next_initial_data(self, form):
        data = form.data.copy()
        # Increment jahr and jahrgang
        data['jahr'] = ", ".join([str(int(j)+len(form.row_data[0].get('jahr'))) for j in form.row_data[0].get('jahr')])
        if form.cleaned_data.get('jahrgang'):  
            data['jahrgang'] = form.cleaned_data.get('jahrgang') + 1
        return data
            
    def instance_data(self, row):
        rslt = {}
        rslt['jahrgang'] = row.get('jahrgang', None)
        rslt['magazin'] = row.get('magazin')
        rslt['info'] = row.get('info', '')
        rslt['status'] = row.get('status')
        return rslt
        
    def build_preview(self, request, form):
        preview_data = []
        headers = []
        preview_fields = []
        row_error = False
        multiple_instances_msg = "Es wurden mehrere passende Ausgaben gefunden. Es soll immer nur eine bereits bestehende Ausgabe verändert werden: diese Zeile wird ignoriert. "
        one_instance_msg = "Es wird ein Dubletten-Bestand zu dieser Ausgabe hinzugefügt."
        
        for row in form.row_data:
            preview_row = OrderedDict()
            for fld_name in form.preview_fields:
                if not fld_name in row:
                    continue
                if fld_name == 'audio':
                    if row.get(fld_name):
                        img = format_html('<img alt="True" src="/static/admin/img/icon-yes.svg">')
                    else:
                        # NOTE: this never happens...
                        img = format_html('<img alt="False" src="/static/admin/img/icon-no.svg">')
                    preview_row[fld_name] = img
                else:
                    values_list = row.get(fld_name) or []
                    if isinstance(values_list, list):
                        if len(values_list)==1:
                            preview_row[fld_name] = values_list[0] or ''
                        else:
                            preview_row[fld_name] = ", ".join(values_list)
                    else:
                        preview_row[fld_name] = values_list or ''
                preview_fields.append(fld_name) # record the field's appearance for the headers creation    
                
            if 'instance' in row:
                instances = [row.get('instance')]
            else:
                instances = list(row.get('multiples', []))
                
            if len(instances)==0:
                preview_row['Instanz'] = '---'
            else:
                links = []
                for instance in instances:
                    link = reverse("admin:DBentry_ausgabe_change", args = [instance.pk])
                    label = str(instance)
                    links.append(format_html('<a href="{}" target="_blank">{}</a>', link, label))
                    
                if len(instances)==1:
                    img = '<img alt="False" src="/static/admin/img/icon-alert.svg">'
                    preview_row['Instanz'] = format_html(img + ", ".join(links))
                    preview_row['Bemerkung'] = one_instance_msg
                else:
                    row_error = True
                    img = '<img alt="False" src="/static/admin/img/icon-no.svg">'
                    preview_row['Instanz'] = format_html(img + ", ".join(links))
                    preview_row['Bemerkung'] = multiple_instances_msg
                    
            preview_data.append(preview_row)
            
        for fld_name in form.preview_fields:
            if fld_name not in preview_fields:
                # This field does not appear at least once in preview_data
                continue
            if form.fields.get(fld_name).label:
                headers.append(form.fields.get(fld_name).label.strip(":"))
            else:
                headers.append(fld_name)
        headers += ['Bereits vorhanden']
        if row_error:
            headers += ['Bemerkung']
        return headers, preview_data

miz_site.register_tool(BulkAusgabe)
miz_site.register_tool(FavoritenView)
