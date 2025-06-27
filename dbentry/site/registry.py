from collections import OrderedDict
from enum import Enum

from django.db.models.base import ModelBase
from django.urls import include, path

from dbentry.utils.url import urlname


class ModelType(Enum):
    ARCHIVGUT = "Archivgut"
    STAMMDATEN = "Stammdaten"
    SONSTIGE = "Sonstige"


class Registry:
    def __init__(self):
        self.views = {}
        self.changelists = {}
        self._model_list = OrderedDict(
            {
                ModelType.ARCHIVGUT.value: [],
                ModelType.STAMMDATEN.value: [],
                ModelType.SONSTIGE.value: [],
            }
        )

    def register_edit(self, models, view):
        for model in models:
            self.views[model] = view

    def register_changelist(self, models, view, category):
        for model in models:
            self._model_list[category].append(model)
            self.changelists[model] = view

    @property
    def model_list(self):
        for category, models in self._model_list.items():
            yield category, sorted([m._meta for m in models], key=lambda opts: opts.verbose_name)

    def get_urls(self):
        from dbentry.site.views.delete import DeleteView
        from dbentry.site.views.export import ExportModelView
        from dbentry.site.views.history import HistoryView

        urlpatterns = []
        for model, view in self.changelists.items():
            opts = model._meta
            urlpatterns.append(path(f"{opts.model_name}/", view.as_view(), name=urlname("changelist", opts)))
            if getattr(view, "resource_class", None):
                urlpatterns.append(
                    path(
                        f"{opts.model_name}/export",
                        ExportModelView.as_view(model=model, resource_classes=[view.resource_class]),
                        name=urlname("export", opts),
                    )
                )
        for model, view in self.views.items():
            opts = model._meta
            patterns = [
                path(
                    "add/",
                    view.as_view(extra_context={"add": True}),
                    name=urlname("add", opts),
                ),
                path(
                    "<path:object_id>/change/",
                    view.as_view(extra_context={"add": False}),
                    name=urlname("change", opts),
                ),
                path(
                    "<path:object_id>/delete/",
                    DeleteView.as_view(model=model),
                    name=urlname("delete", opts),
                ),
                path(
                    "<path:object_id>/history/",
                    HistoryView.as_view(model=model),
                    name=urlname("history", opts),
                ),
                path(
                    "<path:object_id>/view/",
                    view.as_view(model=model, extra_context={"add": False, "view_only": True}),
                    name=urlname("view", opts),
                ),
            ]
            urlpatterns.append(path(f"{opts.model_name}/", include(patterns)))
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls()


miz_site = Registry()


def register_edit(models, site=miz_site):
    """Register an edit (add/change) view for the given models."""
    if isinstance(models, ModelBase):
        models = [models]

    def wrapper(view):
        site.register_edit(models, view)
        return view

    return wrapper


def register_changelist(models, category=ModelType.SONSTIGE, site=miz_site):
    """Register a changelist for the given models."""
    if isinstance(category, ModelType):
        category = category.value
    else:
        try:
            # Check if `category` is a member of the ModelType enum:
            ModelType(category)
        except ValueError:
            raise ValueError(f"'{category}' is an invalid ModelType.") from None

    if isinstance(models, ModelBase):
        models = [models]

    def wrapper(view):
        site.register_changelist(models, view, category)
        return view

    return wrapper
