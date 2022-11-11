from typing import Callable, Type

from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.views import View

from dbentry.actions.views import (
    BulkEditJahrgang, ChangeBestand, MergeView, MoveToBrochure
)


def add_cls_attrs(view_cls: Type[View]) -> Callable:
    """
    A decorator for an action view function that adds view class attributes to
    the function.

    Adds the following attributes to the view function if it doesn't already
    have these set:
        - ``short_description`` (str): which is used as label for the action in
          the changelist drop down menu.
        - ``allowed_permissions``: list of permission codewords required to
          access the action. See dbentry.admin.base.MIZModelAdmin.get_actions()
    """

    def wrap(func: Callable) -> Callable:
        for attr in ('short_description', 'allowed_permissions'):
            if not hasattr(func, attr) and hasattr(view_cls, attr):
                setattr(func, attr, getattr(view_cls, attr))
        return func

    return wrap


@add_cls_attrs(BulkEditJahrgang)
def bulk_jg(model_admin: Model, request: HttpRequest, queryset: QuerySet) -> Callable:
    return BulkEditJahrgang.as_view(model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(MergeView)
def merge_records(model_admin: Model, request: HttpRequest, queryset: QuerySet) -> Callable:
    return MergeView.as_view(model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(MoveToBrochure)
def moveto_brochure(model_admin: Model, request: HttpRequest, queryset: QuerySet) -> Callable:
    return MoveToBrochure.as_view(model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(ChangeBestand)
def change_bestand(model_admin: Model, request: HttpRequest, queryset: QuerySet) -> Callable:
    return ChangeBestand.as_view(model_admin=model_admin, queryset=queryset)(request)
