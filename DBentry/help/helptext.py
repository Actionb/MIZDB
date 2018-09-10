from collections import OrderedDict

from django.contrib.admin.utils import get_fields_from_path
from django.core.exceptions import FieldDoesNotExist
from django.utils.text import capfirst
from django.utils.html import format_html, mark_safe

from .registry import halp
from DBentry.models import *
from DBentry.admin import *
from DBentry.utils import get_model_admin_for_model, is_iterable

def formfield_to_modelfield(model, formfield_name, formfield = None):
    if formfield_name in [field.name for field in model._meta.get_fields()]:
        return model._meta.get_field(formfield_name)
    try:
        return get_fields_from_path(model, formfield_name)[-1]
    except FieldDoesNotExist:
        pass
        
def get_field_helptext(field_name, model):
    if halp.is_registered(model) and hasattr(halp.help_for_model(model), 'fields') \
        and field_name in halp.help_for_model(model).fields:
            return halp.help_for_model(model).fields[field_name]
    return ''
    
class Wrapper(object):
    
    def __init__(self, id, val, label = None):
        self.id = id
        self.val = val
        if label is None:
            self.label = id
        else:
            self.label = label
        
    def __str__(self):
        return str(self.val)
        
    def __repr__(self):
        return "id:{}, label:{}, val:{}".format(self.id, self.label, self.val)
        
    def sidenav(self):
        help_item_bookmark = format_html('<a href="#{id}">{label}</a>', id=self.id, label=capfirst(self.label))
        if not is_iterable(self.val):
            return help_item_bookmark
        return mark_safe(help_item_bookmark + self.html(template = '<li><a href="#{id}">{label}</a></li>'))
            
    def html(self, template = None):
        if not is_iterable(self.val):
            # self.val is either a string or another primitive type
            if not isinstance(self.val, str):
                self.val = str(self.val)
            return format_html('<span id={id}>{text}</span>', id = self.id, text = mark_safe(self.val.strip()))
        
        # self.val is an iterable, i.e. list or tuple, etc.
        if template is None:
            template = '<li id={id} class="{classes}">{label}<br>{text}</li>'
        iterator = []
        for i, v in enumerate(self.val, 1):
            d = dict(
                id = self.id + '-' + str(i), 
                label = str(v), 
                text = '', 
                classes = '', 
            )
            if isinstance(v, dict):
                d.update(v)
                if v.get('label'):
                    d['label'] = mark_safe(v.get('label'))
                if v.get('text'):
                    d['text'] = mark_safe(str(v.get('text')).strip())
                if v.get('classes'):
                    d['classes'] = "".join(c for c in v.get('classes'))
            iterator.append(d)
        return mark_safe("<ul>" + "".join([format_html(template, **i) for i in iterator]) + "</ul>")
        

class BaseHelpText(object):
        
    help_title = ''
    
    help_items = None
    
    def __init__(self, *args, **kwargs):
        if self.help_items is None:
            self.help_items = kwargs.get('help_items', OrderedDict())
        if not isinstance(self.help_items, OrderedDict):
            # Force the help_items into an OrderedDict for easier lookups
            help_items = OrderedDict()
            for index, item in enumerate(self.help_items):
                if not isinstance(item, (list, tuple)):
                    # Assume item is just a single string
                    help_items[item] = item
                elif len(item) >= 2:
                    help_items[item[0]] = item[1]
                else:
                    help_items[item[0]] = item[0]
            self.help_items = help_items
                    
        
    def for_context(self, **kwargs):
        help_items = []
        for id, label in self.help_items.items():
            if id in kwargs:
                help_items.append(kwargs[id])
                continue

            val = getattr(self, id, None)
            if id and val:
                help_items.append(Wrapper(id = id, label = label, val = val))
        return {
            'help_title': self.help_title, 
            'help_items': help_items, 
        }
        
class FormHelpText(BaseHelpText):
    """
    Note that the fields are gathered from the FORM and not the 'FormHelpText.fields' attribute,
    meaning only fields declared on the form will contribute to this help text, any additional fields in FormHelpText.fields that are not on the form 
    will be ignored.
    
    """
    fields = None
    
    form_class = None
    _field_helptexts = None
    
    def __init__(self, *args, **kwargs):
        if self.fields is None:
            self.fields = kwargs.get('fields', {})
        super().__init__(*args, **kwargs)
        
        if 'fields' not in self.help_items:
            # Add the form's fields to the help items
            self.help_items['fields'] = 'fields'
            if len(self.help_items) > 2:
                # Assuming that the deriving HelpText object contains at least a basic 'description' of sorts as the first item,
                # add the field helptexts directly after that description
                first_help_item_key = list(self.help_items.keys())[0]
                self.help_items.move_to_end('fields', last = False) # move fields to the top
                self.help_items.move_to_end(first_help_item_key, last = False) # and move the original first item back to the top
        
    @property
    def field_helptexts(self):
        if self._field_helptexts is None:
            self._field_helptexts = []
            for field_name, formfield in self.get_form().base_fields.items():
                field_helptext = self.get_helptext_for_field(field_name, formfield)
                if field_helptext:
                    self.field_helptexts.append({
                        'id' : field_name, 
                        'label' : formfield.label, 
                        'text': field_helptext, 
                    })
        return self._field_helptexts
        
    def get_form(self):
        if self.form_class:
            return self.form_class(**self.get_form_kwargs())
            
    def get_form_kwargs(self):
        return {}
        
    def get_helptext_for_field(self, field_name, formfield):
        field_helptext = self.fields.get(field_name, '')
        if not field_helptext and formfield.help_text:
            field_helptext = formfield.help_text
        return field_helptext
        
    def for_context(self, **kwargs):
        if self.field_helptexts:
            kwargs['fields'] = Wrapper(id = 'fields', label = self.help_items.get('fields', 'fields'), val = self.field_helptexts)
        return super().for_context(**kwargs)
        
class ModelHelpText(FormHelpText):
    
    model = None
    
    inlines = None
    inline_text = ''
    
    _inline_helptexts = None
    
    def __init__(self, request, model_admin = None, *args, **kwargs):
        if self.inlines is None:
            self.inlines = kwargs.get('inlines', {})
        super().__init__(*args, **kwargs)
        self.request = request
        if not self.help_title:
            self.help_title = capfirst(self.model._meta.verbose_name_plural)
        self.model_admin = model_admin
        if not self.model_admin:
            self.model_admin = get_model_admin_for_model(self.model)
        if 'inlines' not in self.help_items:
            self.help_items['inlines'] = 'inlines'
        
    def for_context(self, **kwargs):
        if self.inline_helptexts:
            kwargs['inlines'] = Wrapper(id = 'inlines', val = self.inline_helptexts)
        return super().for_context(**kwargs)
  
    @property
    def inline_helptexts(self):
        if self._inline_helptexts is None:
            self._inline_helptexts = []
            for inline in self.model_admin.get_inline_instances(self.request):
                inline_model = inline.model
                if getattr(inline, 'verbose_model', False):
                    # inlines that use BaseInlineMixin can have a verbose_model attribute set to the 
                    # 'target' model of a m2m relationship
                    inline_model = inline.verbose_model
                if inline_model._meta.verbose_name_plural in self.inlines:
                    text = self.inlines[inline_model._meta.verbose_name_plural]
                elif halp.is_registered(inline_model) and halp.help_for_model(inline_model).as_inline(self.request):
                        text = halp.help_for_model(inline_model).as_inline(self.request)
                else:
                    continue
                self._inline_helptexts.append({
                    'id' : 'inline-{}'.format(inline_model._meta.verbose_name), 
                    'label' : inline_model._meta.verbose_name_plural, 
                    'text' : text, 
                })
        return self._inline_helptexts
        
    @classmethod
    def as_inline(cls, request, form = None):
        # Display this model's help text from the perspective of a related model
        return cls.inline_text
        
    def get_form(self):
        return self.model_admin.get_form(self.request)
        
    def get_helptext_for_field(self, field_name, formfield):
        if field_name not in self.fields:
            # See if a help text can be extracted through the model field
            model_field = formfield_to_modelfield(self.model, field_name, formfield)
            if model_field.help_text:
                return model_field.help_text
        return super().get_helptext_for_field(field_name, formfield)
        
