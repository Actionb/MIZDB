from ..base import AdminTestCase
from ..mixins import CreateFormViewMixin

class ActionViewTestCase(AdminTestCase, CreateFormViewMixin):

    action_name = ''

    def get_view(self, request=None, args=None, kwargs=None, action_name=None, **initkwargs):
        # Allow setting the action_name and fields attribute and assure model_admin and queryset are passed as initkwargs
        _initkwargs = {'model_admin' : self.model_admin, 'queryset' : self.queryset.all()}
        _initkwargs.update(initkwargs)

        action_name = action_name or self.action_name
        if action_name:
            self.view_class.action_name = action_name

        return super(ActionViewTestCase, self).get_view(request=request, args=args, kwargs=kwargs, **_initkwargs)

