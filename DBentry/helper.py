""" Copy pasta'ed from django.contrib.admin.helpers just to swap a checkbox widget with its label..."""

from django.utils.encoding import force_text
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from django.contrib.admin.helpers import Fieldset, Fieldline, AdminField, AdminReadonlyField

class MIZFieldset(Fieldset):
    
    def __iter__(self):
        for field in self.fields:
            yield MIZFieldline(self.form, field, self.readonly_fields, model_admin=self.model_admin)

class MIZFieldline(Fieldline):

    def __iter__(self):
        for i, field in enumerate(self.fields):
            if field in self.readonly_fields:
                yield AdminReadonlyField(self.form, field, is_first=(i == 0), model_admin=self.model_admin)
            else:
                yield MIZAdminField(self.form, field, is_first=(i == 0))

class MIZAdminField(AdminField):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_checkbox = False

    def label_tag(self):
        classes = []
        contents = conditional_escape(force_text(self.field.label))

        if self.field.field.required:
            classes.append('required')
        if not self.is_first:
            classes.append('inline')
        attrs = {'class': ' '.join(classes)} if classes else {}
        return self.field.label_tag(contents=mark_safe(contents), attrs=attrs, label_suffix='')
