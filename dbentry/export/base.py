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
    for field in model._meta.get_fields():
        if not field.is_relation or field.many_to_one:
            continue

        if field.many_to_many:
            if not field.concrete:
                # Only include m2m relations declared on this model.
                continue
            inline_model = field.remote_field.through
        else:  # field.one_to_many
            inline_model = field.related_model
            if not inline_model._meta.auto_created:
                # FK back from the manual through table of a m2m relation
                # declared on this model. Ignore, since we will use the m2m
                # relation instead.
                continue
        if inline_model not in inlines_by_model:
            # No inline for this model. Assume that this is a relation
            # that users should not see.
            continue
        if inline_model == _models.Bestand:
            # Bestand does not have a name_field
            target_field = "lagerort"
        else:
            target_field = field.related_model.name_field

        inline = inlines_by_model[inline_model]

        path = f"{field.name}__{target_field}"
        name = f"{field.name}_list"
        fields.append(name)
        annotations[name] = f'string_list("{path}")'
        annotated_fields.append(
            f'{name} = Field(attribute="{name}", column_name="{inlines_by_model[inline_model].verbose_name_plural}")'
        )

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
