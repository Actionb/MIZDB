from .base import ActionConfirmationView
    
class BulkEditJahrgang(ActionConfirmationView):
    
    short_description = 'Jahrgang hinzufügen'
    perm_required = ['change']
    
    fields = ['jahrgang']
    
    def action_allowed(self):
        if self.queryset.values('magazin_id').distinct().count() != 1:
            msg_text = "Aktion abgebrochen: ausgewählte Ausgaben stammen von mehr als einem Magazin."
            self.model_admin.message_user(self.request, msg_text, 'error')
            return False
        return True
    
    def perform_action(self, form_cleaned_data):
        #TODO: this is only a placeholder
        if form_cleaned_data:
            self.queryset.order_by().update(jahrgang=form_cleaned_data['jahrgang'])
