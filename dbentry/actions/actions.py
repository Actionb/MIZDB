from typing import Callable, Type

from django.contrib.admin import ModelAdmin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.views import View

from dbentry.actions.views import (
    BulkEditJahrgang, ChangeBestand, MergeView, MoveToBrochure, Replace
)
from dbentry.utils.summarize import get_summaries


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
def bulk_jg(model_admin: ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return BulkEditJahrgang.as_view(model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(MergeView)
def merge_records(model_admin: ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return MergeView.as_view(model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(MoveToBrochure)
def moveto_brochure(model_admin: ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return MoveToBrochure.as_view(model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(ChangeBestand)
def change_bestand(model_admin: ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return ChangeBestand.as_view(model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(Replace)
def replace(model_admin: ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return Replace.as_view(model_admin=model_admin, queryset=queryset)(request)


# noinspection PyUnusedLocal
def summarize(
        model_admin: ModelAdmin,
        request: HttpRequest,
        queryset: QuerySet
) -> HttpResponse:
    """A model admin action that provides a summary for the selected items."""
    response = HttpResponse()
    for d in get_summaries(queryset):
        for k, v in d.items():
            response.write(f'<p>{k}: {v}</p>')
        response.write('<hr style="break-after:page;">')
    return response
# TODO: use a decorator to add attributes to the function
summarize.short_description = 'textuelle Zusammenfassung'  # type: ignore  # noqa
summarize.allowed_permissions = ('view',)  # type: ignore  # noqa
