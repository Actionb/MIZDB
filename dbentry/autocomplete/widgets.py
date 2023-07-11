from mizdb_tomselect.widgets import MIZSelect, MIZSelectTabular

from dbentry import models as _models

# NOTE: models without an explicit create_field (like Person, Autor) still need
# a 'create' field set on the widget or no AJAX requests can be made.


DEFAULTS = {
    (_models.Ausgabe, MIZSelectTabular): {
        "url": "autocomplete_ausgabe",
        "extra_columns": {"jahr_list": "Jahr", "num_list": "Nummer", "lnum_list": "lfd.Nummer"},
        "filter_by": ("ausgabe__magazin", "magazin_id"),
    },
    (_models.Autor, MIZSelect): {"url": "autocomplete_autor", "create_field": "__any__"},
    (_models.Band, MIZSelectTabular): {"extra_columns": {"alias_list": "Aliase"}},
    (_models.Musiker, MIZSelectTabular): {"extra_columns": {"alias_list": "Aliase"}},
    (_models.Person, MIZSelect): {"url": "autocomplete_person", "create_field": "__any__"},
    (_models.Spielort, MIZSelectTabular): {"extra_columns": {"ort___name": "Ort"}},
    (_models.Veranstaltung, MIZSelectTabular): {"extra_columns": {"datum": "Datum", "spielort__name": "Spielort"}},
}


def make_widget(model, tabular=False, namespace="admin", can_add=True, can_list=True, can_edit=True, **kwargs):
    """
    Factory function that creates MIZSelect autocomplete widgets.

    Args:
        model: the model class that provides the choices
        tabular (bool): if True, use MIZSelectTabular as the default widget
        namespace (str): URL namespace for the 'add' and 'changelist' link URLs
        can_add (bool): if True, add an 'add' button
        can_list (bool): if True, add a 'changelist' button
        can_edit (bool): if True, add an 'edit' button to each selected item
        kwargs: additional keyword arguments for the widget class constructor.
          The arguments override those in dbentry.autocomplete.widgets.DEFAULTS.
    """
    if "widget_class" in kwargs:
        widget_class = kwargs.pop("widget_class")
    else:
        if tabular:
            widget_class = MIZSelectTabular
        else:
            widget_class = MIZSelect

    widget_opts = {"model": model, "attrs": {}, **DEFAULTS.get((model, widget_class), {}), **kwargs}
    if "create_field" not in widget_opts and getattr(model, "create_field", None):
        widget_opts["create_field"] = getattr(model, "create_field")

    # Add a placeholder when filtering by the another field:
    if "filter_by" in widget_opts and "placeholder" not in widget_opts["attrs"]:
        field_name, _lookup = widget_opts["filter_by"]
        field_name = " ".join(b.capitalize() for b in field_name.split("_") if b)  # "foo__bar" -> "Foo Bar"
        widget_opts["attrs"]["placeholder"] = f"Bitte zuerst {field_name} auswählen."

    base_pattern = f"{model._meta.app_label}_{model._meta.model_name}"
    if namespace:
        base_pattern = f"{namespace}:{base_pattern}"
    if "add_url" not in widget_opts and can_add:
        widget_opts["add_url"] = f"{base_pattern}_add"
    if "changelist_url" not in widget_opts and can_list:
        widget_opts["changelist_url"] = f"{base_pattern}_changelist"
    if "edit_url" not in widget_opts and can_edit:
        widget_opts["edit_url"] = f"{base_pattern}_change"

    return widget_class(**widget_opts)
