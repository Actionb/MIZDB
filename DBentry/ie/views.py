#
import re

from DBentry.views import MIZAdminView
from .forms import *
from .again import *
from django.shortcuts import render, redirect
from django.views.generic import FormView, TemplateView, ListView

class ImportSelectView(MIZAdminView):
    form_class = ImportSelectForm
    template_name = 'admin/import/import_select.html'
    success_url = 'MIZAdmin:band_or_musiker'
    
#    def __init__(self, file=None, *args, **kwargs):
#        super(ImportSelectView, self).__init__(*args, **kwargs)
#        self.file = file
#        
    def get_initial_data(self, data_list, prefix = 'form', is_band = False, is_musiker = False):
        initial_data = {
            prefix + '-TOTAL_FORMS': str(len(data_list)), 
            prefix + '-INITIAL_FORMS': '0',
            prefix + '-MAX_NUM_FORMS': '',
        }
        for c,  item in enumerate(data_list):
            initial_data[prefix + '-' + str(c) + '-name'] = item
            initial_data[prefix + '-' + str(c) + '-release_ids'] = ", ".join(data_list.get(item, []))
            initial_data[prefix + '-' + str(c) + '-is_band'] = is_band
            initial_data[prefix + '-' + str(c) + '-is_musiker'] = is_musiker
        return initial_data
        
    def get_formset(self, prefix):
        if not hasattr(self.importer, prefix):
            return MBFormSet(extra=0)
        return MBFormSet(self.get_initial_data())
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if '_continue_select' in request.POST:
            from io import TextIOWrapper
            file = TextIOWrapper(request.FILES['import_file'], encoding=request.encoding)
            
            models = [audio, Format, FormatTag, FormatTyp, FormatSize, musiker, band, plattenfirma]
            relations = [Format.audio.field.rel, Format.tag.rel, Format.format_typ.field.rel, Format.format_size.field.rel, audio.plattenfirma.rel]
            
            relations += [audio.band.rel, audio.musiker.rel]
            relation_importer = RelationImport(relations, file=file)
            importer = relation_importer.importer
            
            # Remove band,musiker again 
            del importer.cleaned_data[band]
            del importer.cleaned_data[musiker]
            
            relation_importer.read()
            relation_importer.save()
            
#            relation_importer = RelationImport([audio.band.rel, audio.musiker.rel], file=file, ignore_existing=False)
#            importer = relation_importer.importer
#            relation_importer.read()
            
            if 'check_bom' in request.POST or importer.rest_list:
                request.session['audio_cleaned_data'] = importer.cleaned_data[audio] # Need this in the second stage
                for prefix in ['rest_list', 'musiker_list', 'band_list']:
                    data_list = getattr(importer, prefix)
                    initial_data = self.get_initial_data(data_list, prefix = prefix, is_musiker = 'musiker' in prefix, is_band = 'band' in prefix)
                    context[prefix] = MBFormSet(initial_data, prefix = prefix)
            
                return render(request, 'admin/import/band_or_musiker.html', context = context)
                
            #relation_importer.save()
            
            return render(request, self.template_name, context = context)
        if '_continue_bom' in request.POST:
            relation_importer = RelationImport([audio.band.rel, audio.musiker.rel, audio.person.rel])
            relation_importer.mcs[audio].data = request.session['audio_cleaned_data']
            relation_importer.mcs[musiker].data, relation_importer.mcs[band].data, relation_importer.mcs[person].data = self.build_bom_data(request.POST)
            relation_importer.data_read = True
            relation_importer.save()
            return render(request, self.template_name, context = context)
            
    def build_bom_data(self, post_data):
        forms_done = set()
        musiker_data = []
        band_data = []
        person_data = []
        for k, v in post_data.items():
            regex = re.search(r'-(\d+)-', k)
            if regex is None:
                # Caught a non-form post item
                continue
            form_nr = regex.group(1)
            if form_nr in forms_done:
                continue
            forms_done.add(form_nr)
            prefix = k[:regex.start()]
            field_name = k[regex.end():]
            is_musiker = v if field_name == 'is_musiker' else post_data.get(prefix + '-' + form_nr + '-is_musiker', False)
            is_band = v if field_name == 'is_band' else post_data.get(prefix + '-' + form_nr + '-is_band', False)
            is_person = v if field_name == 'is_person' else post_data.get(prefix + '-' + form_nr + '-is_person', False)
            name = v if field_name == 'name' else post_data.get(prefix + '-' + form_nr + '-name')
            release_ids = v.split(", ") if field_name == 'release_ids' else post_data.get(prefix + '-' + form_nr + '-release_ids').split(", ")
            
            if is_musiker:
                musiker_data.append({'kuenstler_name':name, 'release_id':release_ids})
            if is_band:
                band_data.append({'band_name':name, 'release_id':release_ids})
            if is_person:
                name = name.split()
                nachname = name.pop(-1)
                vorname = " ".join(name)
                person_data.append({'vorname':vorname, 'nachname':nachname, 'release_id':release_ids})
        return musiker_data, band_data, person_data
            
    def build_release_id_map(self, post_data):
        release_id_map = {}
        forms_done = set()
        for k, v in post_data.items():
            regex = re.search(r'-(\d+)-', k)
            if regex is None:
                # Caught a non-form post item
                continue
            form_nr = regex.group(1)
            if form_nr in forms_done:
                continue
            forms_done.add(form_nr)
            prefix = k[:regex.start()]
            field_name = k[regex.end():]
            is_musiker = v if field_name == 'is_musiker' else post_data.get(prefix + '-' + form_nr + '-is_musiker', False)
            is_band = v if field_name == 'is_band' else post_data.get(prefix + '-' + form_nr + '-is_band', False)
            is_person = v if field_name == 'is_person' else post_data.get(prefix + '-' + form_nr + '-is_person', False)
            name = v if field_name == 'name' else post_data.get(prefix + '-' + form_nr + '-name')
            release_ids = v.split(", ") if field_name == 'release_ids' else post_data.get(prefix + '-' + form_nr + '-release_ids').split(", ")
            
            for release_id in release_ids:
                if release_id not in release_id_map:
                    release_id_map[release_id] = {}
                for boolean, model in [(is_musiker, musiker), (is_band, band), (is_person, person)]:
                    if model not in release_id_map[release_id]:
                        release_id_map[release_id][model] = []
                    if boolean:
                        release_id_map[release_id][model].append(name)
        return release_id_map
    
class MBImportView(TemplateView):
    form_class = None
    template_name = 'admin/import/band_or_musiker.html'
    importer = None
    
    def __init__(self, importer = None, *args, **kwargs):
        super(MBImportView, self).__init__(*args, **kwargs)
        self.importer = importer
        self.importer.cleaned_data
        
    def get_context_data(self, **kwargs):
        context = super(MBImportView, self).get_context_data(**kwargs)
        context['importer'] = self.importer
        return context
        
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if '_continue_bom' in request.POST:
            # We are done with this step
            rest_list = MBFormSet(request.POST, request.FILES, prefix='rest_list')
            if rest_list.is_valid():
                pass
            f = open('request_post.txt', 'w')
            for k, v in request.POST.items():
                print(k + ":", file=f)
                print(v, file=f)
                print("="*20, end="\n\n", file=f)
#            f.close()
#            with open('rest_list.txt', 'w') as f:
#                for k, v in 
            return render(request, self.template_name, context = context)
        else:
#            initial = [dict(release_id=", ".join(release_ids), name=item) for item, release_ids in self.importer.rest_list.items()]
#            context['rest_list'] = MBFormSet(initial = initial, prefix='rest_list')
            
            initial = [dict(release_id=", ".join(release_ids), name=item, is_musiker=True) for item, release_ids in self.importer.musiker_list.items()]
            context['musiker_list'] = MBFormSet(initial = initial)
#            
#            initial = [dict(release_id=", ".join(release_ids), name=item, is_band=True) for item, release_ids in self.importer.band_list.items()]
#            context['band_list'] = MBFormSet(initial = initial)
#        
            return render(request, self.template_name, context = context)
        
