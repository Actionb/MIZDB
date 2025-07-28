r"""Factory for generating resource classes.

Generate and write resource classes with this:

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MIZDB.settings.development")
django.setup()

from dbentry.site.views.edit import *  # noqa
from dbentry.export.factory import *  # noqa

if __name__ == '__main__':
    with open("/tmp/mizdb_exports/generated.py", "w") as f:
        for model in miz_site.views:
            resource_class = resource_factory(model)
            f.write(resource_to_string(resource_class)
            f.write("\n\n")
"""

import textwrap
from collections import OrderedDict

from django.core.exceptions import FieldDoesNotExist
from import_export.fields import Field
from import_export.resources import ModelDeclarativeMetaclass

from dbentry import models as _models
from dbentry.export.base import MIZResource
from dbentry.export.fields import AnnotationField, CachedQuerysetField, ChoiceField
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
        # TODO: this should (re-)raise an exception
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
    fields = [model._meta.pk.name, *form_fields]

    # Field overrides for ForeignKeys, select_related and ChoiceFields:
    widgets = {}
    select_related = []
    field_declarations = []
    for field in fields:
        try:
            model_field = model._meta.get_field(field)
        except FieldDoesNotExist:
            continue
        if model_field.is_relation and model_field.many_to_one:
            # Adjust the attribute to export the value of the related object's
            # name field:
            resource_field = Field(
                attribute=f"{model_field.name}__{model_field.related_model.name_field}",
                column_name=model_field.verbose_name,
            )
            field_declarations.append((model_field.name, resource_field))
            select_related.append(model_field.name)
        if getattr(model_field, "choices", None):
            resource_field = ChoiceField(attribute=model_field.name, column_name=model_field.verbose_name)
            field_declarations.append((model_field.name, resource_field))

    # Add AnnotationFields:
    for inline in edit_view.get_inline_instances():
        fk = inline.get_formset_class().fk
        field = get_m2m_field(fk, model) or fk.remote_field
        try:
            target_field = field.related_model.name_field
        except AttributeError:  # pragma: no cover
            print(f"Skipping annotations for '{inline}' inline: {field.related_model} has no 'name_field' set.")
            continue

        name = f"{field.name}_list"
        path = f"{field.name}__{target_field}"
        string_list_kwargs = {}
        if field.related_model == _models.Ort:
            string_list_kwargs["sep"] = "; "
        expression = string_list(path, **string_list_kwargs, length=1024)

        resource_field = CachedQuerysetField(
            attribute=name,
            column_name=inline.verbose_name_plural,
            queryset=model.objects.annotate(**{name: expression}),
        )
        field_declarations.append((name, resource_field))
        fields.append(name)

    if "beschreibung" in form_class.base_fields:
        fields.append("beschreibung")

    # Create the class:
    meta_attrs = {
        "model": model,
        "fields": fields,
        "export_order": fields,
    }
    if widgets:
        meta_attrs["widgets"] = widgets
    if select_related:
        meta_attrs["select_related"] = select_related
    class_attrs = {"Meta": type(str("Meta"), (object,), meta_attrs)}
    for name, field in field_declarations:
        class_attrs[name] = field

    return MIZDeclarativeMetaclass(model.__name__ + str("Resource"), (MIZResource,), class_attrs)


def resource_to_string(resource):
    """Return a string representation of the given resource class."""
    # This is used to write a class generated by the factory to a file.

    # Stringify the extra fields:
    def string_list_from_expr(original_expr):
        # Inspect the expression to recover the original arguments:
        # string_list expressions: limit(array_to_string(array_agg(...)))
        array_to_string = original_expr._constructor_args[0][0]
        array_agg, sep_expr, default_expr = array_to_string.source_expressions
        path = array_agg.source_expressions[0].name
        sep = sep_expr.value
        if sep != ", ":
            return f'string_list("{path}", sep="{sep}", length=1024)'
        else:
            return f'string_list("{path}", length=1024)'

    field_declarations = []
    if getattr(resource._meta, "_declared_fields", None):
        for name, field in resource._meta._declared_fields.items():
            field_kwargs = f'attribute="{field.attribute}", column_name="{field.column_name}"'
            if isinstance(field, AnnotationField):
                field_kwargs = f"{field_kwargs}, expr={string_list_from_expr(field.expr)},"
            elif isinstance(field, CachedQuerysetField):
                expr = string_list_from_expr(field.queryset.query.annotations[name])
                queryset = f"_models.{resource._meta.model.__name__}.objects.annotate({name}={expr})"
                field_kwargs = f"{field_kwargs}, queryset={queryset},"
            field_declarations.append(f"{name} = {field.__class__.__name__}({field_kwargs})")

    # Collect any extra meta:
    extra_meta = []
    if getattr(resource._meta, "widgets", None):
        widgets = str(resource._meta.widgets).replace("'", '"')
        extra_meta.append(f"widgets = {widgets}")
    if getattr(resource._meta, "select_related", None):
        select_related = str(resource._meta.select_related).replace("'", '"')
        extra_meta.append(f"select_related = {select_related}")

    indent = " " * 4
    template = textwrap.dedent(
        """
        class %(model_name)sResource(MIZResource):
            %(field_declarations)s

            class Meta:
                model = _models.%(model_name)s
                fields = %(fields)s
                export_order = %(fields)s
                %(extra_meta)s

        """
    )
    return template % {
        "model_name": resource._meta.model.__name__,
        "field_declarations": f"\n{indent}".join(field_declarations),
        "fields": str(resource._meta.fields).replace("'", '"'),
        "extra_meta": f"\n{indent * 2}".join(extra_meta),
    }
