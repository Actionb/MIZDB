from tests.case import AdminTestCase, ViewTestCase, DataTestCase


class ActionViewTestCase(DataTestCase, ViewTestCase):
    action_name = ""

    def get_view(self, request=None, args=None, kwargs=None, action_name=None, **initkwargs):
        initkwargs = {
            "queryset": self.queryset.all(),
            "action_name": action_name or self.action_name,
            **initkwargs,
        }
        return super().get_view(request=request, args=args, kwargs=kwargs, **initkwargs)


class AdminActionViewTestCase(AdminTestCase, ActionViewTestCase):
    def get_view(self, request=None, args=None, kwargs=None, action_name=None, **initkwargs):
        initkwargs["model_admin"] = self.model_admin
        return super().get_view(request=request, args=args, kwargs=kwargs, **initkwargs)
