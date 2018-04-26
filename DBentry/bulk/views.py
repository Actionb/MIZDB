 
from collections import OrderedDict
from itertools import chain
 
from django import views    
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError

from DBentry.views import MIZAdminToolViewMixin
from DBentry.utils import link_list
from DBentry.models import ausgabe, audio, m2m_audio_ausgabe
from DBentry.logging import LoggingMixin
from DBentry.sites import register_tool
from .forms import BulkFormAusgabe

@register_tool
class BulkAusgabe(MIZAdminToolViewMixin, views.generic.FormView, LoggingMixin):
    
    template_name = 'admin/bulk.html'
    form_class = BulkFormAusgabe
    success_url = 'admin:DBentry_ausgabe_changelist'
    url_name = 'bulk_ausgabe' #TODO: remove this? NOPE! Used in the admin_site.index
    index_label = 'Ausgaben Erstellung' # label for the tools section on the index page
    
    _permissions_required = [('add', 'ausgabe')]
    
    def get_initial(self):
        # If there was a form 'before' the current one, its data will serve as initial values 
        # This way, we can track changes to the form the user has made.
        return self.request.session.get('old_form_data', {})
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = self.get_form()
        
        if form.is_valid():
            if form.has_changed() or '_preview' in request.POST:
                # the form's data differs from initial -- or the user has requested a preview
                if not '_preview' in request.POST:
                    # the form has changed and the user did not request a preview, complain about it
                    messages.warning(request, 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.')
                context['preview_headers'], context['preview'] = self.build_preview(request, form)
            else:
                if '_continue' in request.POST:
                    # save the data and redirect back to the changelist
                    ids, instances, updated = self.save_data(form)
                    # Need to store the ids of the newly created items in request.session so the changelist can filter for them
                    request.session['qs'] = dict(id__in=ids) if ids else None
                    return redirect(self.success_url) #TODO: make this open in a popup/new tab
                    
                if '_addanother' in request.POST:   
                    # save the data, notify the user about changes and prepare the next view
                    old_form = form
                    ids, created, updated = self.save_data(form)
                    
                    if created:
                        obj_list = link_list(request, created)
                        messages.success(request, format_html('Ausgaben erstellt: {}'.format(obj_list)))
                    if updated:
                        obj_list = link_list(request, updated)
                        messages.success(request, format_html('Dubletten hinzugefügt: {}'.format(obj_list)))
                    
                    # Prepare the form for the next view
                    form = self.form_class(self.next_initial_data(form))
                    # clean it
                    form.is_valid()
                    # and add the preview
                    context['preview_headers'], context['preview'] = self.build_preview(request, form)
                    # Add the 'next' form for the next view to render
                    context['form'] = form
                    
        # Provide the next form with initial so we can track data changes within the form
        request.session['old_form_data'] = form.data
        return self.render_to_response(context)
    
    @transaction.atomic()
    def save_data(self, form):
        #TODO: update instance attributes (jahrgang,etc.)?
        ids = [] # contains the pks of instances either created or updated by save_data
        created = [] # contains instances of objects that were newly created by save_data
        updated = [] # contains instances that were existed before save_data and were updated by it
        
        original = [] # any unique row or the first row in a set of equal rows 
        dupes = [] # rows in this list are a duplicate of a row in originals, no new objects will be created for duplicate rows, but a 'dubletten' bestand will be added to their originals
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
                
        for row in chain(original, dupes):
            if 'dupe_of' in row:
                instance = row['dupe_of']['instance'] # this cannot fail, since we've saved all original instances before
                bestand_data = dict(lagerort=row.get('lagerort')) # since this is a dupe_of another row, form.row_data has set lagerort to dublette
                if 'provenienz' in row['dupe_of']:
                    # Also add the provenienz of the original to this object's bestand
                    bestand_data['provenienz'] = row.get('provenienz')
                b = instance.bestand_set.create(**bestand_data)
                self.log_addition(instance, b)
                continue
            
            instance = row.get('instance', None) or ausgabe(**self.instance_data(row)) 
            if not instance.pk:
                # this is a new instance, mark it as such
                instance.save()
                self.log_addition(instance)
                created.append(instance)
            else:
                # this instance already existed, mark it as updated
                updated.append(instance)
            
            # Create and/or update sets
            for fld_name in ['jahr', 'num', 'monat', 'lnum']:
                set = getattr(instance, "ausgabe_{}_set".format(fld_name))
                data = row.get(fld_name, None)
                if data:
                    if fld_name == 'monat':
                        fld_name = 'monat_id'
                    if not isinstance(data, (list, tuple)):
                        data = [data]
                    for value in data:
                        if value:
                            try:
                                with transaction.atomic():
                                    o = set.create(**{fld_name:value})
                            except IntegrityError as e: 
                                # ignore UNIQUE constraints violations
                                continue
                            else:
                                self.log_addition(instance, o)
            
            # all the necessary data to construct a proper name should be included now, update the name
            instance.update_name(force_update=True)
                
            # Audio
            if 'audio' in row:
                suffix = instance.__str__()
                audio_data = dict(titel = 'Musik-Beilage: {}'.format(str(row.get('magazin'))) + " " + suffix, 
                                                    quelle = 'Magazin', 
                                                    e_jahr = row.get('jahr')[0],
                                                    )
                                                    
                if audio.objects.filter(**audio_data).exists():
                    audio_instance = audio.objects.filter(**audio_data).first()
                else:
                    audio_instance = audio(**audio_data)
                    audio_instance.save()
                    self.log_addition(audio_instance)
                    
                if not m2m_audio_ausgabe.objects.filter(ausgabe=instance, audio=audio_instance).exists():
                    # avoid UNIQUE constraints violations
                    m2m_instance = m2m_audio_ausgabe(ausgabe=instance, audio=audio_instance)
                    m2m_instance.save()
                    self.log_addition(instance, m2m_instance)
                    self.log_addition(audio_instance, m2m_instance)
                    
                bestand_data = dict(lagerort=form.cleaned_data.get('audio_lagerort'))
                if 'provenienz' in row:
                    bestand_data['provenienz'] = row.get('provenienz')
                    
                b = audio_instance.bestand_set.create(**bestand_data)
                self.log_addition(audio_instance, b)
                
            # Bestand
            bestand_data = dict(lagerort=row.get('lagerort'))
            if 'provenienz' in row:
                bestand_data['provenienz'] = row.get('provenienz')
            b = instance.bestand_set.create(**bestand_data)
            self.log_addition(instance, b)
            
            row['instance'] = instance
            ids.append(instance.pk)
        return ids, created, updated
                
    def next_initial_data(self, form):
        # Using form.cleaned_data would insert model instances into the data we are going to save in request.session... and model instances are not JSON serializable
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
        rslt['beschreibung'] = row.get('beschreibung', '')
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
                    img = format_html('<img alt="True" src="/static/admin/img/icon-yes.svg">')
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
        
    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(opts=ausgabe._meta)
