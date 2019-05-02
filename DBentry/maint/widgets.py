from django import forms

class ColumnedCheckboxWidget(forms.CheckboxSelectMultiple):
    template_name = 'admin/widgets/multiple_input_columns.html'
    
    def __init__(self, *args, **kwargs):
        self.showgroups = kwargs.pop('showgroups', False) # Whether or the widget will render the names of groups in choices
        super().__init__(*args, **kwargs)
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['showgroups'] = self.showgroups
        return context
        
    
