from ..base import *

class ACViewTestCase(ViewTestCase, LoggingTestMixin):
    
    model = None
    create_field = None
    
    def view(self, request=None, args=None, kwargs=None, model = None, create_field = None, forwarded = None, q = None):
        #DBentry.ac.views behave slightly different in their as_view() method
        self.view_class.model = model or self.model
        self.view_class.create_field = create_field or self.create_field
        self.view_class.forwarded = forwarded or {}
        self.view_class.q = q or ''
        return super(ACViewTestCase, self).view(request, args, kwargs)
