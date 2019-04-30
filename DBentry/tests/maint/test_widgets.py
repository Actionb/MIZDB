from ..base import MyTestCase

from django import forms
from django.template.exceptions import TemplateDoesNotExist

from DBentry.maint.widgets import ColumnedCheckboxWidget

class TestWidget(MyTestCase):
    
    def test_widget_template_found(self):
        widget = ColumnedCheckboxWidget()
        with self.assertNotRaises(TemplateDoesNotExist):
            widget.render(1, 1)
        
        # If the widget has choices, the template will include the option's templates. 
        # Need to check if that sub template is accessible also.
        widget = ColumnedCheckboxWidget(choices = [('a', 1), ('b', 2)])
        with self.assertNotRaises(TemplateDoesNotExist):
            widget.render(1, 1)
    
    def test_widget_render_no_groups(self):
        # Assert that the div to create the columns is not added if there are no groups in choices.
        widget = ColumnedCheckboxWidget(choices = [('a', 1), ('b', 2)])
        self.assertNotIn(widget.render(1, 1), '<div style="flex: 50%;">')
        
    def test_widget_render_with_groups(self):
        # Assert that the div to create the columns is added if there are no groups in choices.
        widget = ColumnedCheckboxWidget(choices = [('Group1', [('a', 1)]), ('Group2', [('b', 2)])])
        self.assertEqual(widget.render(1, 1).count('<div style="flex: 50%;">'), 2, 
            msg = "Rendered output should contain two groups.")
        
    def test_form_can_render(self):
        form = type('F',(forms.Form,),{'a':forms.CharField(widget=ColumnedCheckboxWidget(choices = [('a', 1), ('b', 2)]))})()
        with self.assertNotRaises(TemplateDoesNotExist):
            str(form)
