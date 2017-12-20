import re
from itertools import chain

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
         
class BulkField(forms.CharField):
    
    allowed_special = [',', '/', '-', '*']
    allowed_space = True
    allowed_numerical = True
    allowed_alpha = False    
    
    def __init__(self, required=False, 
            allowed_special = None, allowed_space = None, allowed_numerical = None, allowed_alpha = None, 
            *args, **kwargs):
        super(BulkField, self).__init__(required=required,  *args, **kwargs)
        
        self.allowed_special = allowed_special or self.allowed_special
        self.allowed_space = self.allowed_space if allowed_space is None else allowed_space
        self.allowed_numerical = self.allowed_numerical if allowed_numerical is None else allowed_numerical
        self.allowed_alpha = self.allowed_alpha if allowed_alpha is None else allowed_alpha
        
        msg_text = 'Unerlaubte Zeichen gefunden:'
        if self.allowed_numerical:
            msg_text += ' Bitte nur Ziffern'
        else:
            msg_text += ' Bitte nur Buchstaben'
        msg_text += ' (plus Buchstaben-Kürzel)' if self.allowed_alpha and self.allowed_numerical else ''
        msg_text += ' oder ' if self.allowed_special else ''
        msg_text += ' oder '.join(['"'+s+'"' for s in self.allowed_special]) + ' benutzen.'
        self.error_messages['invalid'] = _(msg_text)
        
    def widget_attrs(self, widget):
        attrs = super(BulkField, self).widget_attrs(widget)
        attrs['style'] = 'width:350px;'
        return attrs
        
    @property
    def regex(self):
        regex = re.compile(r'|'.join(
            chain(
                map(re.escape, self.allowed_special), 
                [r'\s+'] if self.allowed_space else [], 
                [r'[0-9]'] if self.allowed_numerical else [], 
                [r'[a-zA-Z]'] if self.allowed_alpha else [], 
            )
        ))
        return regex
        
        
    def validate(self, value):
        super(BulkField, self).validate(value)
        if any(self.regex.search(c) is None for c in value):
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        
    def clean(self, value):
        value = super(BulkField, self).clean(value)
        value = value.strip()
        if value and value[-1] in self.allowed_special:
            # Strip accidental last delimiter
            value = value[:-1]
        return value
        
    def to_list(self, value):
        if not value:
            return [], 0
        temp = []
        item_count = 0
        for item in value.split(','):
            item = item.strip()
            if item:
                if item.count('-')==1:
                    if item.count("*") == 1:
                        item,  multi = item.split("*")
                        multi = int(multi)
                    else:
                        multi = 1
                    s, e = (int(i) for i in item.split("-"))
                    
                    for i in range(s, e+1, multi):
                        temp.append([str(i+j) for j in range(multi)])
                        item_count += 1
                elif '/' in item:
                    temp.append([i for i in item.split('/') if i])
                    item_count += 1
                else:
                    temp.append(item)
                    item_count += 1
        return temp, item_count
        
class BulkJahrField(BulkField):
    
    allowed_special = [',', '/']
    
    def clean(self, value):
        # Normalize Jahr values into years seperated by commas only
        # Also correct the year if year is a shorthand
        value = super(BulkJahrField, self).clean(value)
        clean_values = []
        for item in value.replace('/', ',').split(','):
            item = item.strip()
            if len(item)==2:
                if int(item) <= 17:
                    item = '20' + item
                else:
                    item = '19' + item
            clean_values.append(item)
        return ','.join(clean_values)
        
    def to_list(self, value):
        temp, item_count = super(BulkJahrField, self).to_list(value)
        return temp, 0
        
