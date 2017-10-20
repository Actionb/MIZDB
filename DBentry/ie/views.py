#
import re

from DBentry.views import MIZAdminView
from .forms import *
from .discogs import *
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
            
#            from django.core.files.storage import FileSystemStorage
#            fs = FileSystemStorage()
#            filename = fs.save(file.name, file)
#            uploaded_file_url = fs.url(filename)
            
#            context['file_url'] = uploaded_file_url
            # TODO: fetch importer_class from request.POST
            importer_class = FullImporter
            importer = importer_class([musiker, band], file=file)
            importer.cleaned_data
            
            
            if 'check_bom' in request.POST or importer.rest_list:
                for prefix in ['rest_list', 'musiker_list', 'band_list']:
                    data_list = getattr(self.importer, prefix)
                    initial_data = self.get_initial_data(data_list, prefix = prefix, is_musiker = 'musiker' in prefix, is_band = 'band' in prefix)
                    context[prefix] = MBFormSet(initial_data, prefix = prefix)
            
            #return ImportSelectView.as_view({'file':file})(request)
                return render(request, 'admin/import/band_or_musiker.html', context = context)   
        if '_continue_bom' in request.POST:
            release_id_map = self.build_release_id_map(request.POST)
#            with open('release_id_map.txt', 'w') as f:
#                for release_id, models in release_id_map.items():
#                    print("release_id:", release_id, file=f)
#                    for model, names in models.items():
#                        print(model._meta.model_name+":", ", ".join(names), file=f)
#                    print("="*20, end="\n\n", file=f)
            
            # We are done with this step
#                f = open('request_post.txt', 'w')
#                for k, v in request.POST.items():
#                    print(k + ":", file=f)
#                    print(v, file=f)
#                    print("="*20, end="\n\n", file=f)
#                f.close()
            #self.importer_class([musiker, band], file=file, release_id_map=release_id_map)
            #print(self.importer.cleaned_data[musiker])
            return render(request, self.template_name, context = context)
            
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
        
