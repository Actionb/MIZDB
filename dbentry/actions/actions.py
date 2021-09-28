from typing import Callable

from django.db.models import Model, QuerySet
from django.http import HttpRequest

from dbentry.actions.decorators import add_cls_attrs
from dbentry.actions.views import (
    BulkEditJahrgang, ChangeBestand, MergeViewWizarded, MoveToBrochureBase
)


@add_cls_attrs(BulkEditJahrgang)
def bulk_jg(model_admin: Model, request: HttpRequest, queryset: QuerySet) -> Callable:
    return BulkEditJahrgang.as_view(
        model_admin=model_admin, queryset=queryset
    )(request)


@add_cls_attrs(MergeViewWizarded)
def merge_records(model_admin: Model, request: HttpRequest, queryset: QuerySet) -> Callable:
    return MergeViewWizarded.as_view(
        model_admin=model_admin, queryset=queryset
    )(request)


@add_cls_attrs(MoveToBrochureBase)
def moveto_brochure(model_admin: Model, request: HttpRequest, queryset: QuerySet) -> Callable:
    return MoveToBrochureBase.as_view(
        model_admin=model_admin, queryset=queryset
    )(request)


@add_cls_attrs(ChangeBestand)
def change_bestand(model_admin: Model, request: HttpRequest, queryset: QuerySet) -> Callable:
    return ChangeBestand.as_view(
        model_admin=model_admin, queryset=queryset
    )(request)
