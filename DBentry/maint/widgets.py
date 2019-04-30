from django import forms
from django.forms.renderers import TemplatesSetting
from django.utils.safestring import mark_safe

class ColumnedCheckboxWidget(forms.CheckboxSelectMultiple):
    template_name = 'admin/widgets/multiple_input_columns.html'
    
    
##    def render(self, name, value, attrs=None, renderer=None):
###        kwargs['renderer'] = forms.renderers.TemplatesSetting()
##        _renderer = forms.renderers.TemplatesSetting()
##        return super().render(name, value, attrs, _renderer)
#        
#    def _render(self, template_name, context, renderer=None):
#        template = TemplatesSetting().get_template(self.template_name)
#        return mark_safe(template.render(context))
        
    
