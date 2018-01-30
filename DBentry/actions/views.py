
from django.db import transaction
from django.utils.html import format_html
from django.contrib.admin.utils import get_fields_from_path

from .base import ActionConfirmationView
from .forms import BulkAddBestandForm

from DBentry.utils import link_list
from DBentry.models import *
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID
    
class BulkEditJahrgang(ActionConfirmationView):
    
    short_description = 'Jahrgang hinzufügen'
    perm_required = ['change']
    action_name = 'bulk_jg'
    
    initial = {'jahrgang':1}
    fields = ['jahrgang']
    help_texts = {'jahrgang':'Wählen sie den Jahrgang für das erste Jahr.'}
    
    #TODO: FUCK GRAMMATIK
    view_helptext = """ Sie können hier Jahrgänge zu den ausgewählten Ausgaben hinzufügen.
                        Dabei wird das früheste Jahr in der Auswahl als Startpunkt aufgefasst und der Wert für den Jahrgang für jedes weitere Jahr entsprechend hochgezählt.
                        Den Ausgaben, die keine Jahresangaben besitzen, wird nur der von Ihnen unten gewählte Wert für Jahrgang zugewiesen.
    """
    
    def action_allowed(self):
        if self.queryset.values('magazin_id').distinct().count() != 1:
            msg_text = "Aktion abgebrochen: ausgewählte Ausgaben stammen von mehr als einem Magazin."
            self.model_admin.message_user(self.request, msg_text, 'error')
            return False
        return True
    
    def perform_action(self, form_cleaned_data):
        qs = self.queryset.order_by().all()
        jg = form_cleaned_data['jahrgang']
        
        years_in_qs = qs.values_list('ausgabe_jahr__jahr', flat = True).exclude(ausgabe_jahr__jahr=None).order_by('ausgabe_jahr__jahr').distinct()
        previous_year = years_in_qs.first()
        with transaction.atomic():
            # Update all the objects that do not have a year
            qs.filter(ausgabe_jahr__jahr=None).update(jahrgang=jg)
            
            # Update all the objects that do have a year, and increment the jahrgang accordingly
            for year in years_in_qs:
                jg += year - previous_year
                loop_qs = qs.filter(ausgabe_jahr__jahr=year)
                loop_qs.update(jahrgang=jg)
                # Do not update the same issue twice (e.g. issues with two years)
                qs = qs.exclude(ausgabe_jahr__jahr=year)
                previous_year = year
                
                
class BulkAddBestand(ActionConfirmationView):
    
    short_description = 'Bestand hinzufügen'
    perm_required = ['alter_bestand']
    action_name = 'add_bestand'
    
    form_class = BulkAddBestandForm
    fields = ['bestand']
    #TODO: make initials dependent of the view's model
    initial = {'bestand' : lagerort.objects.get(pk=ZRAUM_ID), 'dublette' : lagerort.objects.get(pk=DUPLETTEN_ID)}
    
    view_helptext = """ Sie können hier Bestände für die ausgewählten Objekte hinzufügen.
                        Besitzt ein Objekt bereits einen Bestand in der ersten Kategorie ('Lagerort (Bestand)'), so wird stattdessen diesem Objekt ein Bestand in der zweiten Kategorie ('Lagerort (Dublette)') hinzugefügt.
    """
       
    def perform_action(self, form_cleaned_data):
        
        base_msg = "{lagerort}-Bestand zu diesen {count} {verbose_model_name} hinzugefügt: {obj_links}"
        format_dict = {'verbose_model_name':self.opts.verbose_name_plural}
        
        bestand_lagerort = form_cleaned_data['bestand']
        dupletten_lagerort = form_cleaned_data['dublette']
        
        bestand_list = []
        dubletten_list = []
        # Get the correct fkey from bestand model to this view's model
        fkey = get_fields_from_path(self.opts.model, 'bestand')[0].field
        
        for instance in self.queryset:
            if not bestand.objects.filter(**{fkey.name:instance, 'lagerort':bestand_lagerort}):
                bestand_list.append(bestand(**{fkey.name:instance, 'lagerort':bestand_lagerort}))
            else:
                dubletten_list.append(bestand(**{fkey.name:instance, 'lagerort':dupletten_lagerort}))
                
        with transaction.atomic():
            if bestand_list:
                bestand.objects.bulk_create(bestand_list)
                obj_links = link_list(self.request, [getattr(z, fkey.name) for z in bestand_list])
                format_dict.update({'lagerort': str(bestand_lagerort), 'count':len(bestand_list), 'obj_links': obj_links})
                msg_text = base_msg.format(**format_dict)
                self.model_admin.message_user(self.request, format_html(msg_text))
            
            if dubletten_list:
                bestand.objects.bulk_create(dubletten_list)
                obj_links = link_list(self.request, [getattr(z, fkey.name) for z in dubletten_list])
                format_dict.update({'lagerort': str(dupletten_lagerort), 'count':len(dubletten_list), 'obj_links': obj_links})
                msg_text = base_msg.format(**format_dict)
                self.model_admin.message_user(self.request, format_html(msg_text))
            
