from typing import List, Tuple, Type, Union

from django.core import exceptions
from django.db.models import Field, Model
from django.db.models.constants import LOOKUP_SEP

from dbentry.utils.models import get_fields_and_lookups


def get_dbfield_from_path(
        model: Union[Model, Type[Model]], field_path: str
) -> Tuple[Field, List[str]]:
    """
    Return the final, concrete target field of a field path and the lookups
    used on that path.

    Raises:
        - FieldDoesNotExist (from utils.get_fields_and_lookups):
            if the field_path does not resolve to an existing model field.
        - FieldError (from utils.get_fields_and_lookups):
            if an invalid lookup was used.
        - FieldError: if the field_path results in a reverse relation
    """
    fields, lookups = get_fields_and_lookups(model, field_path)
    db_field = fields[-1]
    if not db_field.concrete:
        # 'db_field' is a relation object.
        raise exceptions.FieldError("Reverse relations not supported.")
    return db_field, lookups


def strip_lookups_from_path(path: str, lookups: List[str]) -> str:
    """
    Remove the lookups from the path.

    ('datum__jahr__in', ['in']) -> 'datum__jahr'
    """

    def filter_func(piece: str) -> bool:
        """Filter out lookups."""
        return piece not in lookups

    return LOOKUP_SEP.join(
        (path.split(LOOKUP_SEP)[0], *filter(filter_func, path.split(LOOKUP_SEP)[1:]))
    )
