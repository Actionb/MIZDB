from typing import Callable

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy

from dbentry.actions.views import AdminMergeView, BulkEditJahrgang, ChangeBestand, MoveToBrochure, Replace, text_summary


@admin.action(description=gettext_lazy("Add issue volume"), permissions=["change"])
def bulk_jg(model_admin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return BulkEditJahrgang.as_view(model_admin=model_admin, queryset=queryset)(request)


@admin.action(description=gettext_lazy("Merge selected %(verbose_name_plural)s"), permissions=["merge"])
def merge_records(model_admin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return AdminMergeView.as_view(model_admin=model_admin, queryset=queryset)(request)


@admin.action(description="zu Broschüren bewegen", permissions=["moveto_brochure"])
def moveto_brochure(model_admin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return MoveToBrochure.as_view(model_admin=model_admin, queryset=queryset)(request)


@admin.action(description="Bestände ändern", permissions=["alter_bestand"])
def change_bestand(model_admin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return ChangeBestand.as_view(model_admin=model_admin, queryset=queryset)(request)


@admin.action(description="%(verbose_name)s ersetzen", permissions=["superuser"])
def replace(model_admin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet) -> Callable:
    return Replace.as_view(model_admin=model_admin, queryset=queryset)(request)


@admin.action(description="textuelle Zusammenfassung", permissions=["view"])
def summarize(_model_admin: admin.ModelAdmin, _request: HttpRequest, queryset: QuerySet) -> HttpResponse:
    """An admin action that provides a text summary for the selected items."""
    return text_summary(queryset)
