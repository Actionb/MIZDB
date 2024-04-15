from collections import OrderedDict

from django.core.exceptions import FieldDoesNotExist
from django.utils.encoding import force_str
from import_export.fields import Field
from import_export.resources import ModelDeclarativeMetaclass, ModelResource

from dbentry import models as _models
from dbentry.site.registry import miz_site
from dbentry.site.views.edit import *  # register the views with miz_site # noqa
from dbentry.utils.query import string_list


class MIZDeclarativeMetaclass(ModelDeclarativeMetaclass):
    def __new__(cls, name, bases, attrs):
        # Keep a record of the fields that were declared on this model:
        _declared_fields = OrderedDict()
        for _name, attr in attrs.items():
            if isinstance(attr, Field):
                _declared_fields[_name] = attr

        new_class = super().__new__(cls, name, bases, attrs)

        new_class._meta._declared_fields = _declared_fields

        return new_class


class MIZResource(ModelResource):
    add_annotations = True

    def _add_annotations(self, queryset):
        """Add the annotations declared in Meta.annotations to the queryset."""
        if self.add_annotations:
            return queryset.annotate(**self._meta.annotations)
        else:
            return queryset

    def filter_export(self, queryset, *args, **kwargs):
        return self._add_annotations(queryset)

    def get_export_headers(self):
        # For fields derived from the model fields, use the field's
        # verbose_name, unless column_name was set:
        headers = []
        for field in self.get_export_fields():
            try:
                model_field = self._meta.model._meta.get_field(field.attribute)
                verbose_name = model_field.verbose_name.capitalize()
            except FieldDoesNotExist:
                verbose_name = field.column_name
            if field.column_name != field.attribute:
                # Not the default column_name
                headers.append(force_str(field.column_name))
            else:
                headers.append(force_str(verbose_name))
        return headers

    def as_string(self):
        """Return a string representation of this model resource class."""
        # This is used to write a generated class to a file.

        indent = " " * 4
        r = f"class {self.__class__.__name__}(MIZResource):\n"

        # Stringify the annotation fields:
        if self._meta._declared_fields:
            for name, field in self._meta._declared_fields.items():
                r += f'{indent}{name} = Field(attribute="{field.attribute}", column_name="{field.column_name}")\n'
            r += "\n"

        # Stringify the Meta class:
        r += f"{indent}class Meta:\n"
        indent *= 2

        r += f"{indent}model = _models.{self._meta.model.__name__}\n"

        fields = str(self._meta.fields).replace("'", '"')
        r += f"{indent}fields = {fields}\n{indent}export_order = {fields}\n"

        if self._meta.annotations:
            _annotations = OrderedDict()
            for name, expr in self._meta.annotations.items():
                # Inspect the expression to recover the original arguments:
                # string_list expressions: limit(array_to_string(array_agg(...)))
                array_to_string = expr.source_expressions[0]
                array_agg, sep_expr, default_expr = array_to_string.source_expressions
                path = array_agg.source_expressions[0].name
                sep = sep_expr.value
                if sep != ", ":
                    annotation = f'string_list("{path}", sep="{sep}")'
                else:
                    annotation = f'string_list("{path}")'
                _annotations[name] = annotation
            _annotations = ", ".join(f'"{name}": {expr}' for name, expr in _annotations.items())
            r += f"{indent}annotations = {{{_annotations}}}\n"

        if self._meta.widgets:
            widgets = str(self._meta.widgets).replace("'", '"')
            r += f"{indent}widgets = {widgets}\n"

        return r


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


def resource_factory(model):
    """
    Create a ModelResource class for the given model.

    This uses the model's edit view to collect fields (from the view's form)
    and to create the right annotations (from the view's inlines).
    """
    try:
        edit_view = miz_site.views[model](extra_context={"add": True})
    except KeyError:
        print(f"No view for model '{model}'.")
        return

    # Collect the meta attributes and field declarations.
    # Base fields:
    form_class = edit_view.get_form_class()
    form_fields = []
    for field_name in form_class.base_fields:
        try:
            model._meta.get_field(field_name)
        except FieldDoesNotExist:
            # Do not add fields that are not part of the model
            continue
        if field_name not in ("beschreibung", "bemerkungen"):
            form_fields.append(field_name)
    fields = ["id", *form_fields]

    # Widget overrides:
    widgets = {}
    for field in fields:
        try:
            model_field = model._meta.get_field(field)
        except FieldDoesNotExist:
            continue
        if model_field.is_relation and model_field.many_to_one:
            # Set the widget field to the name_field of the related model:
            widgets[model_field.name] = {"field": model_field.related_model.name_field}

    # Additional fields and their annotations:
    annotations = OrderedDict()
    field_declarations = []
    for inline in edit_view.get_inline_instances():
        fk = inline.get_formset_class().fk
        field = get_m2m_field(fk, model) or fk.remote_field
        if inline.model == _models.Bestand:
            # NOTE: Bestand does not have a name_field set
            target_field = "lagerort___name"
        else:
            target_field = field.related_model.name_field

        name = f"{field.name}_list"
        path = f"{field.name}__{target_field}"

        string_list_kwargs = {}
        if field.related_model == _models.Ort:
            string_list_kwargs["sep"] = "; "
        annotations[name] = string_list(path, **string_list_kwargs)
        fields.append(name)

        field_declarations.append((name, Field(attribute=name, column_name=inline.verbose_name_plural)))

    if "beschreibung" in form_class.base_fields:
        fields.append("beschreibung")

    # Create the class:
    meta_attrs = {
        "model": model,
        "fields": fields,
        "export_order": fields,
        "annotations": annotations,
        "widgets": widgets,
    }
    class_attrs = {"Meta": type(str("Meta"), (object,), meta_attrs)}
    for name, field in field_declarations:
        class_attrs[name] = field

    return MIZDeclarativeMetaclass(model.__name__ + str("Resource"), (MIZResource,), class_attrs)
