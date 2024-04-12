from collections import OrderedDict

from dbentry import models as _models
from dbentry.site.registry import miz_site


def get_resource_attributes_for_model(model):
    """
    Return required attributes for the ModelResource for the given model.

    Returns a 3-tuple of:
        - a list of field names for the `field` meta attribute
        - a dictionary of annotations for the `annotations` meta attribute
        - a list of Field declarations for the resource class body
    """
    try:
        edit_view = miz_site.views[model](extra_context={"add": True})
    except KeyError:
        print(f"No view for model '{model}'.")
        return

    # base fields
    form_class = edit_view.get_form_class()
    form_fields = [f for f in form_class.base_fields if f not in ("beschreibung", "bemerkungen")]
    fields = ["id", *form_fields]

    # relations with annotations
    annotations = {}
    annotated_fields = []
    inlines = edit_view.get_inline_instances()
    inlines_by_model = {inline.model: inline for inline in inlines}
    annotations_by_inline = OrderedDict((inline, None) for inline in inlines)
    for field in model._meta.many_to_many:
        print(field)
        inline_model = field.remote_field.through if field.concrete else field.through
        if inline_model not in inlines_by_model:
            # No inline for this model - assume this isn't for end-users.
            continue
        inline = inlines_by_model[inline_model]
        path = f"{field.name}__{field.related_model.name_field}"
        name = f"{field.name}_list"
        annotations_by_inline[inline] = (name, path, inline.verbose_name_plural)

    for field in model._meta.get_fields():
        if not field.one_to_many:
            continue
        inline_model = field.related_model
        if inline_model not in inlines_by_model:
            continue
        inline = inlines_by_model[inline_model]
        if annotations_by_inline[inline] is not None:
            # Already done for this inline (used a m2m relation).
            continue
        if inline_model == _models.Bestand:
            # Bestand does not have a name_field
            target_field = "lagerort"
        else:
            target_field = field.related_model.name_field

        path = f"{field.name}__{target_field}"
        name = f"{field.name}_list"
        annotations_by_inline[inline] = (name, path, inline.verbose_name_plural)

    for inline, data in annotations_by_inline.items():
        if data is None:
            print(f"No data for inline: '{inline}'")
            continue
        name, path, verbose_name = data
        fields.append(name)
        annotations[name] = f'string_list("{path}")'
        annotated_fields.append(f'{name} = Field(attribute="{name}", column_name="{verbose_name}")')

    if "beschreibung" in form_class.base_fields:
        fields.append("beschreibung")
    # TODO: order annotations according to the order of inlines
    return fields, annotations, annotated_fields


template = """
class %(model_name)sResource(MIZResource):
    %(annotation_fields)s

    class Meta:
        model = _models.%(model_name)s
        fields = [%(fields)s]
        export_order = [%(fields)s]
        annotations = {%(annotations)s}

"""


def print_model_resource(model):
    """Print a ModelResource declaration for the given model."""
    fields, annotations, annotated_fields = get_resource_attributes_for_model(model)
    print(
        template % {
            "model_name": model.__name__,
            "fields": ", ".join(f'"{field}"' for field in fields) + ",",
            "annotations": ", ".join(f'"{name}": {annotation}' for name, annotation in annotations.items()) + ",",
            "annotation_fields": "\n\t".join(annotated_fields),
        }
    )
