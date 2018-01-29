
from django.db import transaction

from .base import ActionConfirmationView
from .forms import BulkAddBestandForm
    
class BulkEditJahrgang(ActionConfirmationView):
    
    short_description = 'Jahrgang hinzufügen'
    perm_required = ['change']
    action_name = 'bulk_jg'
    
    fields = ['jahrgang']
    
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
            for year in years_in_qs:
                jg += year - previous_year
                loop_qs = qs.filter(ausgabe_jahr__jahr=year)
                loop_qs.update(jahrgang=jg)
                # Do not update the same issue twice (e.g. issues with two years)
                qs = qs.exclude(ausgabe_jahr__jahr=year)
                previous_year = year
                
                
class BulkAddBestand(ActionConfirmationView):
    
    short_description = 'Bestand hinzufügen'
    perm_required = ['change']
    action_name = 'add_bestand'
    
    form_class = BulkAddBestandForm
    fields = ['bestand']
    
    def perform_action(self, form_cleaned_data):
        pass
