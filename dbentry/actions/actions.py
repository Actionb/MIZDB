from dbentry.actions.views import (
    BulkEditJahrgang, MergeViewWizarded, MoveToBrochureBase,
    ChangeBestand
)
from dbentry.actions.decorators import add_cls_attrs
# TODO: add an action that creates an overview of the stock (Bestand) of the
# selected items (possibly allow changes there too?)


@add_cls_attrs(BulkEditJahrgang)
def bulk_jg(model_admin, request, queryset):
    return BulkEditJahrgang.as_view(
        model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(MergeViewWizarded)
def merge_records(model_admin, request, queryset):
    return MergeViewWizarded.as_view(
        model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(MoveToBrochureBase)
def moveto_brochure(model_admin, request, queryset):
    return MoveToBrochureBase.as_view(
        model_admin=model_admin, queryset=queryset)(request)


@add_cls_attrs(ChangeBestand)
def change_bestand(model_admin, request, queryset):
    return ChangeBestand.as_view(
        model_admin=model_admin, queryset=queryset)(request)
