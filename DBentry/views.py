from collections import OrderedDict

from django.shortcuts import render, redirect
from django.http import HttpResponse

from django.db.models.fields import AutoField, related
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.utils.translation import ugettext as _
from django.contrib.admin.utils import get_fields_from_path
from django.utils.html import format_html

from .models import *
from .forms import *
from .utils import link_list

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
                del self._flds[i]
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
        return qs
        
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
        return provenienz.objects.create(geber=geber.objects.create(name=text))
        
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
                
from django.contrib import admin
from django.contrib import messages
from django.views.generic import FormView
class MIZAdminView(FormView):
    form_class = None
    template_name = None
    
    def dispatch(self, request, *args, **kwargs):
        kwargs.update(admin.site.each_context(request))
        return super(MIZAdminView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Default get method of ProcessFormView calls get_context_data withouth kwargs (site_header, site_titel, etc.) 
        # which we want on all our views
        return render(request, self.template_name, context = self.get_context_data(**kwargs))
        
#
#class BulkBase(MIZAdminView):
#    template_name = 'admin/bulk.html'
#    form_class = None
#    success_url = ''
#    
#    def post(self, request, *args, **kwargs):
#        context = self.get_context_data(**kwargs)
#        form = self.form_class(request.POST, initial=request.session.get('old_form_data', {}))
#        if form.is_valid():
#            if form.has_changed() or '_preview' in request.POST:
#                if not '_preview' in request.POST:
#                    messages.warning(request, 'Angaben haben sich geändert. Bitte kontrolliere diese in der Vorschau.')
#                context['preview_headers'], context['preview'] = self.build_preview(request, form)
#            else:
#                if '_continue' in request.POST and not form.has_changed():
#                    # Collect preview data, create instances
#                    ids, instances = self.save_data(request, form)
#                    # Need to store the queryset of the newly created items in request.session for the Changelist view
#                    request.session['qs'] = dict(id__in=ids) if ids else None
#                    return redirect(self.success_url)
#                if '_addanother' in request.POST and not form.has_changed():
#                    old_form = form
#                    ids, created, updated = self.save_data(request, form)
#                    from django.core.urlresolvers import reverse
#                    if created:
#                        obj_list = link_list(request, created, path = "admin:DBentry_ausgabe_change")
#                        messages.success(request, format_html('Ausgaben erstellt: {}'.format(obj_list)))
#                    if updated:
#                        obj_list = link_list(request, updated, path = "admin:DBentry_ausgabe_change")
#                        messages.success(request, format_html('Dubletten hinzugefügt: {}'.format(obj_list)))
#                    
#                    form = self.form_class(self.next_initial_data(form))
#                    form.is_valid()
#                    context['preview_headers'], context['preview'] = self.build_preview(request, form)
#        request.session['old_form_data'] = form.data
#        context['form'] = form
#        return render(request, self.template_name, context = context)
#    
#    def next_initial_data(self, form):
#        return form.data
#    
#    def save_data(self, request, form):
#        return []
#        
#    def build_preview(self, request, form):
#        return 
#        
#    def instance_data(self, row):
#        return {}
#        #TODO: this is WIP
#        for fld_name in form.each_fields:
#            if fld_name in form.split_data:
#                continue
#                rslt[fld_name] = form.split_data.get(fld_name)
#            else:
#                rslt[fld_name] = form.cleaned_data.get(fld_name)
#        return rslt

class BulkAusgabe(MIZAdminView):
    template_name = 'admin/bulk.html'
    form_class = BulkFormAusgabe
    success_url = 'admin:DBentry_ausgabe_changelist'
    
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
                    from django.core.urlresolvers import reverse
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
        from django.contrib.admin.utils import reverse
        from django.utils.html import format_html
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
