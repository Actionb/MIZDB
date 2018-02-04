
from .views import BulkEditJahrgang, BulkAddBestand, MergeViewWizarded
from .decorators import add_cls_attrs

@add_cls_attrs(BulkEditJahrgang)
def bulk_jg(model_admin, request, queryset):
    return BulkEditJahrgang.as_view(model_admin=model_admin, queryset=queryset)(request)

@add_cls_attrs(BulkAddBestand)
def add_bestand(model_admin, request, queryset):
    return BulkAddBestand.as_view(model_admin=model_admin, queryset=queryset)(request)
    
@add_cls_attrs(MergeViewWizarded)
def merge_records(model_admin, request, queryset):
    return MergeViewWizarded.as_view(model_admin=model_admin, queryset=queryset)(request)