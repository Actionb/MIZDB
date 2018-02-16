import re

from DBentry.views import MIZAdminToolViewMixin
from .forms import ImportSelectForm, MBFormSet
from .relational import RelationImport
from .name_utils import split_name
from DBentry.models import *
from django.shortcuts import render, redirect
from django import views
from DBentry.sites import register_tool

@register_tool
class ImportSelectView(MIZAdminToolViewMixin, views.generic.FormView):
    form_class = ImportSelectForm
    template_name = 'admin/import/import_select.html'
    url_name = 'import_select'
    index_label = 'Discogs Import'
    
    @staticmethod 
    def show_on_index_page(request): 
        return request.user.is_superuser 
        
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
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)            
        relations = [Format.audio.field.rel, Format.tag.rel, Format.format_typ.field.rel, Format.format_size.field.rel, audio.plattenfirma.rel]
        relations += [audio.band.rel, audio.musiker.rel]
        if '_continue_select' in request.POST:
            from io import TextIOWrapper
            file = TextIOWrapper(request.FILES['import_file'], encoding='utf-8')
            
            models = [audio, Format, FormatTag, FormatTyp, FormatSize, musiker, band, plattenfirma]
            relations = [Format.audio.field.rel, Format.tag.rel, Format.format_typ.field.rel, Format.format_size.field.rel, audio.plattenfirma.rel]
            relations += [audio.band.rel, audio.musiker.rel]
            
            relation_importer = RelationImport(relations, file=file)
            importer = relation_importer.importer
             
            relation_importer.read()
            
            if 'check_bom' in request.POST or importer.rest_list:
                for model, mc in relation_importer.mcs.items():
                    request.session[model._meta.model_name + '_cleaned_data'] = mc.data
                for prefix in ['rest_list', 'musiker_list', 'band_list']:
                    
                    data_list = getattr(importer, prefix)
                    initial_data = self.get_initial_data(data_list, prefix = prefix, is_musiker = 'musiker' in prefix, is_band = 'band' in prefix)
                    context[prefix] = MBFormSet(initial_data, prefix = prefix)
            
                return render(request, 'admin/import/band_or_musiker.html', context = context)
                
            relation_importer.save()
            
            return render(request, self.template_name, context = context)
        if '_continue_bom' in request.POST:
            
            ffs = [MBFormSet(request.POST, prefix=prefix) for prefix in ['rest_list', 'musiker_list', 'band_list']]
            
            if all(fs.is_valid() for fs in ffs):
                relations.append(audio.person.rel)
                relation_importer = RelationImport(relations)
                for model, mc in relation_importer.mcs.items():
                    mc.data = request.session.get(model._meta.model_name + '_cleaned_data')            
                
                relation_importer.mcs[musiker].data, relation_importer.mcs[band].data, relation_importer.mcs[person].data = self.build_bom_data(request.POST)
                relation_importer.data_read = True
                relation_importer.save()
                for model, mc in relation_importer.mcs.items():
                    try:
                        del request.session[model._meta.model_name + '_cleaned_data']
                    except:
                        continue
                return render(request, self.template_name, context = context)
            else:
                # TODO: get the 'updated' version of these prefix lists
                context.update({prefix:ffs[i] for i, prefix in enumerate(['rest_list', 'musiker_list', 'band_list'])})
                return render(request, 'admin/import/band_or_musiker.html', context = context)
                
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
            prefix = k[:regex.start()]
            if (prefix, form_nr) in forms_done:
                continue
            forms_done.add((prefix, form_nr))
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
                vorname, nachname = split_name(name)
                person_data.append({'vorname':vorname, 'nachname':nachname, 'release_id':release_ids})
        return musiker_data, band_data, person_data
