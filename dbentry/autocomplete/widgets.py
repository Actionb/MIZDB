from mizdb_tomselect.widgets import MIZSelect, MIZSelectTabular, MIZSelectTabularMultiple, MIZSelectMultiple

from dbentry import models as _models

# NOTE: models without an explicit create_field (like Person, Autor) still need
# a 'create' field set on the widget or no AJAX requests can be made.


DEFAULTS = {
    _models.Ausgabe: {
        "url": "autocomplete_ausgabe",
        "extra_columns": {"jahr_list": "Jahr", "num_list": "Nummer", "monat_list": "Monat", "lnum_list": "lfd.Nummer"},
        "filter_by": ("ausgabe__magazin", "magazin_id"),
        "attrs": {"placeholder": "Bitte zuerst ein Magazin auswählen"},
    },
    _models.Autor: {"url": "autocomplete_autor", "create_field": "__any__"},
    _models.Band: {"extra_columns": {"alias_list": "Aliase", "orte_list": "Orte"}},
    _models.Magazin: {"url": "autocomplete_magazin"},
    _models.Musiker: {"extra_columns": {"alias_list": "Aliase", "orte_list": "Orte"}},
    _models.Person: {"url": "autocomplete_person", "create_field": "__any__"},
    _models.Spielort: {"extra_columns": {"ort___name": "Ort"}},
    _models.Veranstaltung: {"extra_columns": {"datum": "Datum", "spielort__name": "Spielort"}},
    _models.Provenienz: {"url": "autocomplete_provenienz", "label_field": "text"},
    _models.Schlagwort: {"url": "autocomplete_schlagwort"},
    _models.Genre: {"url": "autocomplete_genre"},
}


class MIZMediaMixin:
    """Add a custom init script to the widget's media."""

    class Media:
        js = ["mizdb/js/mizselect_init.js"]


def make_widget(
    model,
    tabular=False,
    multiple=False,
    namespace="",
    can_add=True,
    can_list=True,
    can_edit=True,
    **kwargs,
):
    """
    Factory function that creates MIZSelect autocomplete widgets.

    Args:
        model: the model class that provides the choices
        tabular (bool): if True, use MIZSelectTabular as the default widget
        multiple (bool): if True, use a select multiple variant of the widget
        namespace (str): URL namespace for the 'add' and 'changelist' link URLs
        can_add (bool): if True, add an 'add' button
        can_list (bool): if True, add a 'changelist' button
        can_edit (bool): if True, add an 'edit' button to each selected item
        kwargs: additional keyword arguments for the widget class constructor.
          The arguments override those in dbentry.autocomplete.widgets.DEFAULTS.
    """
    widget_class = kwargs.pop("widget_class", None)
    widget_opts = {"model": model, "attrs": {}, **DEFAULTS.get(model, {}), **kwargs}
    if "extra_columns" in widget_opts:
        tabular = True

    if widget_class is None:
        if not tabular and not multiple:
            widget_class = MIZSelect
        elif tabular and not multiple:
            widget_class = MIZSelectTabular
        elif tabular and multiple:
            widget_class = MIZSelectTabularMultiple
        else:
            widget_class = MIZSelectMultiple
        widget_class = type("AutocompleteWidget", (MIZMediaMixin, widget_class), {})

    if tabular and "value_field_label" not in widget_opts:
        widget_opts["value_field_label"] = "ID"

    if "create_field" not in widget_opts and getattr(model, "create_field", None):
        widget_opts["create_field"] = getattr(model, "create_field")

    # Add a placeholder when filtering by the another field:
    if "filter_by" in widget_opts and "placeholder" not in widget_opts["attrs"]:
        field_name, _lookup = widget_opts["filter_by"]
        # TODO: placeholder should target the field of the lookup (filter_by[1])
        #  instead of the field path (filter_by[0])?
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
