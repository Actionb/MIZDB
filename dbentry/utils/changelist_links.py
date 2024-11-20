"""Functions for creating so-called changelist links.

A changelist link is a link on the edit or view page of an object to the
changelist of objects that it is related with.

For example, assuming that a Band object is related with multiple Artikel
objects, then the changelist link for Artikel on that Band's edit page would
send the user to the Artikel changelist page, filtered to only include the
Artikel objects that the Band is related with.

Changelist links only cover reverse relations that are not already handled by
inlines on the edit page. That means that the relation Band <-> Musiker does
not get a changelist link since that relation is handled by an inline.

This way, changelist links mostly cover relations towards "Archivgut" objects,
since Stammdaten <-> Stammdaten (f.ex. Band <-> Musiker) and
Archivgut <-> Stammdaten (f.ex. Artikel <-> Band) should be handled by inlines
and thus be excluded.
"""

from typing import Type, Callable, Optional

from django.db import models
from django.db.models import ForeignObjectRel
from django.urls import NoReverseMatch, reverse
from django.utils.text import capfirst

from dbentry.utils.models import get_model_relations


def get_changelist_link_relations(
    model: Type[models.Model], inline_models: list[ForeignObjectRel]
) -> list[ForeignObjectRel]:
    """
    Return a list of relations for which changelist links should be created.

    Exclude relations already covered by inlines.

    Args:
        model (Model): the model for which to create the changelist links
        inline_models (sequence of Models): the list of model classes of the
            edit view's inlines
    """
    relations = []
    inline_models = inline_models or []
    for rel in get_model_relations(model, forward=False, reverse=True):
        if rel.many_to_many:
            inline_model = rel.through
        else:
            inline_model = rel.related_model
        if inline_model in inline_models:
            continue
        relations.append(rel)
    return relations


def get_rel_info(model: Type[models.Model], rel: ForeignObjectRel) -> tuple[Type[models.Model], str]:
    """
    Return the related model and the remote field for the given relation from
    the perspective of the given model.

    Return the related model and the name of the remote field to query against,
    from the perspective of the given model following the given relation.

    Args:
        model (model): the model of the edit page
        rel (relation): the relation that the changelist link should follow
    """
    query_model = rel.related_model
    query_field = rel.remote_field.name
    if rel.many_to_many and query_model == model._meta.model:
        # M2M relations are symmetric, but we wouldn't want to create
        # a changelist link that leads back to *this* model's changelist
        # (unless it's a self relation).
        query_model = rel.model
        query_field = rel.name
    return query_model, query_field


def get_relation_count(model: Type[models.Model], object_id: int, rel: ForeignObjectRel) -> int:
    """
    Return the count of the objects that the object with the given model and
    object ID is related to over the given relation.

    Args:
        model (model): the model of the edit page
        object_id (int): the primary key of the edit page object
        rel (relation): the relation that the changelist link should follow
    """
    query_model, query_field = get_rel_info(model, rel)
    return query_model.objects.filter(**{query_field: object_id}).count()


def get_changelist_link_url(
    model: Type[models.Model], object_id: int, rel: ForeignObjectRel, url_callback: Callable
) -> Optional[str]:
    """
    Return the URL for the changelist link to the changelist page of the
    related objects.

    Takes a callback that should return the reversible URL name to the
    changelist page of the related model
    (f.ex. 'admin:dbentry_artikel_changelist').

    Args:
        model (model): the model of the edit page
        object_id (int): the primary key of the edit page object
        rel (relation): the relation that the changelist link should follow
        url_callback (callable): a callable that takes the relation model and
          returns the URL name for the changelist of the relation model
    """
    query_model, query_field = get_rel_info(model, rel)
    try:
        return f"{reverse(url_callback(query_model))}?{query_field}={object_id}"
    except NoReverseMatch:
        return None


def get_changelist_link_label(
    model: Type[models.Model], rel: ForeignObjectRel, labels: Optional[dict[str, str]] = None
) -> str:
    """
    Return the label for the changelist link for the given relation.

    Args:
        model (model): the model of the edit page
        rel (relation): the relation that the changelist link should follow
        labels (dict): a dictionary of model names to label overrides for
            changelist links towards that model
    """
    query_model, query_field = get_rel_info(model, rel)
    if labels and query_model._meta.model_name in labels:
        label = labels[query_model._meta.model_name]
    elif rel.related_name:
        label = " ".join(capfirst(s) for s in rel.related_name.split("_"))
    else:
        label = query_model._meta.verbose_name_plural
    return label
