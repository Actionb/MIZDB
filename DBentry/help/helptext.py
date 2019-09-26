from collections import OrderedDict

from django.contrib.admin.utils import get_fields_from_path
from django.core.exceptions import FieldDoesNotExist
from django.utils.text import capfirst
from django.utils.html import format_html, mark_safe

from DBentry.utils import get_model_admin_for_model, is_iterable

def formfield_to_modelfield(model, formfield_name, formfield=None):
    if formfield_name in [field.name for field in model._meta.get_fields()]:
        return model._meta.get_field(formfield_name)
    try:
        return get_fields_from_path(model, formfield_name)[-1]
    except FieldDoesNotExist:
        pass
        
class HTMLWrapper(object):
    """
    Wraps the help item to provide the two methods sidenav() and html() for use on the template.
    """
    
    def __init__(self, id, val, label=None):
        self.id = id # the id of the html element 
        self.val = val # either a string representing the help text or a list of dictionaries of: 'list item header': 'list item help text'
        if label is None:
            self.label = id
        else:
            self.label = label
        
    def __str__(self):
        return str(self.val)
        
    def __repr__(self):
        return "id:{}, label:{}, val:{}".format(self.id, self.label, self.val)
        
    def sidenav(self):
        """
        Returns side navigation bookmarks to the help item(s).
        """
        help_item_bookmark = format_html('<a href="#{id}">{label}</a>', id=self.id, label=capfirst(self.label))
        if not is_iterable(self.val):
            return help_item_bookmark
        # This help item contains a sublist.
        return mark_safe(help_item_bookmark + self.html(template='<li><a href="#{id}">{label}</a></li>'))
            
    def html(self, template=None):
        """
        Returns a html representation of the help item.
        If the help item is simple text, it will surround the the text with <span> elements,
        otherwise an unordered list is used, with the text bits as list items.
        """
        if not is_iterable(self.val):
            # self.val is either a string or another primitive type
            if not isinstance(self.val, str):
                self.val = str(self.val)
            return format_html('<span id={id}>{text}</span>', id=self.id, text=mark_safe(self.val.strip()))
        
        # self.val is an iterable, i.e. list or tuple, etc.
        if template is None:
            template = '<li id={id} class="{classes}">{label}<br>{text}</li>'
        iterator = []
        for i, v in enumerate(self.val, 1):
            d = dict(
                id=self.id + '-' + str(i), 
                label=str(v), 
                text='', 
                classes='', 
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
    """
    The base class of all help texts.
    
    Attributes:
        - index_title: the title used for this help text on the index page
        - help_items: an iterable that contains the attribute names of help texts declared on this instance.
                These names can either be simple strings or 2-tuples containing the name of the attribute and a label.
    """
        
    index_title = ''
    site_title = breadcrumbs_title = ''
    
    help_items = None
    
    def __init__(self):
        if self.help_items is None:
            self.help_items = OrderedDict()
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
        """
        Prepare this help text to be used as context data for a template.
        This includes wrapping help items in html.
        """
        help_items = []
        for id, label in self.help_items.items():
            if id in kwargs:
                # This help item was explicitly passed in through the kwargs.
                # Assume it is already wrapped and ready for use.
                help_items.append(kwargs[id])
                continue

            val = getattr(self, id, None)
            if id and val:
                help_items.append(HTMLWrapper(id=id, label=label, val=val))
        context = {'help_items': help_items}
        if self.site_title:
            context['site_title'] = self.site_title
        if self.breadcrumbs_title:
            context['breadcrumbs_title'] = self.breadcrumbs_title
        return context

class FormViewHelpText(BaseHelpText):
    """
    The basic container for help texts to a form view.
    
    It gathers help texts for each formfield from this instance's 'fields' mapping or the formfield's helptext attribute.
    Note that this means that any additional help text for fields that are not declared on the form will be ignored.
    The fields' helptexts will be inserted as the second item, unless specifically set otherwise in 'help_items'.
    
    Attributes:
        - fields: a mapping of formfield name to a help text
        - form_class: the class of the form this HelpText object is based off
        - target_view_class: the view this HelpText object is based off
    """
    fields = None
    
    form_class = None
    _field_helptexts = None
    
    target_view_class = None
    
    def __init__(self):
        if self.fields is None:
            self.fields = {}
        if self.form_class is None and self.target_view_class is not None:
            # Get the form class from the target FormView
            self.form_class = self.target_view_class.form_class
        if not self.index_title:
            self.index_title = 'Hilfe für ' + str(self.form_class)
            
        super().__init__()
        
        if 'fields' not in self.help_items:
            # Add the form's fields to the help items
            self.help_items['fields'] = 'fields'
            if len(self.help_items) > 2:
                # Assuming that the deriving HelpText object contains at least a basic 'description' of sorts as the first item,
                # add the field helptexts directly after that description
                first_help_item_key = list(self.help_items.keys())[0]
                self.help_items.move_to_end('fields', last=False) # move fields to the top
                self.help_items.move_to_end(first_help_item_key, last=False) # and move the original first item back to the top
        
    @property
    def field_helptexts(self):
        """
        Collect the help texts for each field of the form.
        """
        if self._field_helptexts is None:
            self._field_helptexts = []
            for field_name, formfield in self.get_form().base_fields.items():
                field_helptext = self.get_helptext_for_field(field_name, formfield)
                if field_helptext:
                    self.field_helptexts.append({
                        'id': field_name, 
                        'label': formfield.label, 
                        'text': field_helptext, 
                    })
        return self._field_helptexts
        
    def get_form(self):
        if self.form_class:
            return self.form_class(**self.get_form_kwargs())
            
    def get_form_kwargs(self):
        return {}
        
    def get_helptext_for_field(self, field_name, formfield):
        """
        Returns the help text for a particular formfield.
        First, it looks up the formfield's name in the local 'fields' mapping, failing that, it uses the formfield's helptext.
        """
        field_helptext = self.fields.get(field_name, '')
        if not field_helptext and formfield.help_text:
            field_helptext = formfield.help_text
        return field_helptext
        
    def for_context(self, **kwargs):
        if self.field_helptexts:
            kwargs['fields'] = HTMLWrapper(id='fields', label=self.help_items.get('fields', 'fields'), val=self.field_helptexts)
        return super().for_context(**kwargs)
        
class ModelAdminHelpText(FormViewHelpText):
    """
    The help text for a model admin that provides help texts for the inlines.
    The inline help texts will be appended to the end of the help items.
    
    Attributes:
        - model: duh
        - inlines: a mapping of inline model (or the inline's verbose_model) to a help text
        - inline_text: a short help text for when this model is viewed as an inline by another model admin
    """
    model = None
    
    inlines = None
    inline_text = ''
    
    _inline_helptexts = None
    
    def __init__(self, request, registry, model_admin=None):
        self.request = request
        self.registry = registry
        self.model_admin = model_admin or get_model_admin_for_model(self.model)
        
        # Set defaults for index_title, site_title and breadcrumbs_title
        if not self.index_title:
            self.index_title = capfirst(self.model._meta.verbose_name_plural)
        if not self.breadcrumbs_title:
            self.breadcrumbs_title = self.model_admin.opts.verbose_name_plural
        if not self.site_title:
            self.site_title = self.model_admin.opts.verbose_name_plural + ' Hilfe'
            
        super().__init__()
        
        if not self.inlines:
            self.inlines = {}
        elif 'inlines' not in self.help_items:
            # Add an 'inlines' help item if there is at least one inline
            self.help_items['inlines'] = 'inlines'
        
    def for_context(self, **kwargs):
        if self.inline_helptexts:
            kwargs['inlines'] = HTMLWrapper(id='inlines', val=self.inline_helptexts)
        return super().for_context(**kwargs)
  
    @property
    def inline_helptexts(self):
        """
        Collect the help texts for each inline of the model admin.
        If the inline's model cannot be found in this instance's 'inlines' mapping, attempt to get the *inline* version of 
        the help text of that model from the registered help texts.
        """
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
                elif self.registry.helptext_for_model(inline_model) and self.registry.helptext_for_model(inline_model).as_inline(self.request):
                    text = self.registry.helptext_for_model(inline_model).as_inline(self.request)
                else:
                    continue
                self._inline_helptexts.append({
                    'id': 'inline-{}'.format(inline_model._meta.verbose_name), 
                    'label': inline_model._meta.verbose_name_plural, 
                    'text': text, 
                })
        return self._inline_helptexts
        
    @classmethod
    def as_inline(cls, request, form=None):
        """
        Display this model's help text from the perspective of a related model.
        """
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
        
