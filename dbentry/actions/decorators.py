# TODO: move this into actions.py
from typing import Callable, Type

from django.views import View


def add_cls_attrs(view_cls: Type[View]) -> Callable:
    """
    A decorator for an action view function that adds view class attributes.

    Adds the following attributes to the view function if it doesn't already
    have these set:
        - ``short_description`` (str): which is used as label for the action in
          the changelist drop down menu.
        - ``allowed_permissions``: list of permission codewords required to
          access the action. See dbentry.admin.base.MIZModelAdmin.get_actions()
    """

    def wrap(func):
        if (not hasattr(func, 'short_description')
                and hasattr(view_cls, 'short_description')):
            func.short_description = view_cls.short_description
        if (not hasattr(func, 'allowed_permissions')
                and hasattr(view_cls, 'allowed_permissions')):
            func.allowed_permissions = view_cls.allowed_permissions
        return func

    return wrap
