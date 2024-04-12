from dbentry import models as _models
from dbentry.site.registry import miz_site


# TODO: ForeignKeys need to present an actual human-readable value to the
#  dataset. Currently, it's just an id.


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

    annotations, annotated_fields = get_resource_annotations(model, edit_view.get_inline_instances())
    fields.extend(annotations.keys())

    if "beschreibung" in form_class.base_fields:
        fields.append("beschreibung")
    return fields, annotations, annotated_fields


def get_m2m_field(fk, model):
    """
    Return the ManyToManyField that uses the given ForeignKey's model as a
    m2m 'through' table.

    Returns None if no ManyToManyField could be found (probably because the fk
    does not implement a m2m relation).
    """
    for f in model._meta.get_fields():
        if not f.many_to_many or f.one_to_many:
            continue
        remote_field = f.remote_field if f.concrete else f
        if remote_field.through == fk.model:
            return f


def get_resource_annotations(model, inlines):
    """Derive annotations for the model resource from the inlines."""
    annotations = {}
    annotated_fields = []
    for inline in inlines:
        formset_class = inline.get_formset_class()
        fk = formset_class.fk
        field = get_m2m_field(fk, model)
        if field is None:
            # Just a M2O field pointing at model.
            field = fk.remote_field
        if inline.model == _models.Bestand:
            # Bestand does not have a name_field
            # TODO: declare 'OVERRIDES' at module level:
            #  OVERRIDES = {_models.Bestand: "lagerort___name"}
            target_field = "lagerort___name"
        else:
            target_field = field.related_model.name_field

        name = f"{field.name}_list"
        path = f"{field.name}__{target_field}"
        annotations[name] = f'string_list("{path}")'
        annotated_fields.append(f'{name} = Field(attribute="{name}", column_name="{inline.verbose_name_plural}")')

    return annotations, annotated_fields


template = """
class %(model_name)sResource(MIZResource):
    %(annotation_fields)s

    class Meta:
        model = _models.%(model_name)s
        fields = [%(fields)s]
        export_order = [%(fields)s]
        annotations = {%(annotations)s}

"""


def print_model_resource(model, file=None):
    """Print a ModelResource declaration for the given model."""
    fields, annotations, annotated_fields = get_resource_attributes_for_model(model)
    print(
        template % {
            "model_name": model.__name__,
            "fields": ", ".join(f'"{field}"' for field in fields),
            "annotations": ", ".join(f'"{name}": {annotation}' for name, annotation in annotations.items()),
            "annotation_fields": f"\n{' ' * 4}".join(annotated_fields),
        },
        file=file
    )
