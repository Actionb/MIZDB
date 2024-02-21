from typing import Union, Any, Optional

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import Value, Func, Expression
from django.db.models.expressions import Combinable

LENGTH_LIMIT = 100


def to_array(path: str, ordering: str = "", distinct: bool = True) -> ArrayAgg:
    """
    Aggregate objects from `path` into an array.

    The items will be ordered according to the order given by `ordering`.
    If `ordering` is empty, order by `path` instead.
    """
    return ArrayAgg(path, ordering=ordering or path, distinct=distinct)


def join_arrays(*arrays: Expression) -> Func:
    """Return an expression that joins the arrays."""
    return Func(*arrays, function="array_cat", output_field=models.CharField())


def array_remove(array: Expression, remove: Optional[Any] = None) -> Func:
    """Remove all elements equal to the given value from the array."""
    return Func(array, Value(remove), function="array_remove")


def array_to_string(*arrays: Expression, sep: str = ", ", null: str = "-") -> Func:
    """
    String concatenate the objects in the arrays.

    The items will be separated by `sep`.
    Empty items will be replaced by the string `null`.
    """
    if len(arrays) > 1:
        array = array_remove(join_arrays(*arrays))
    else:
        array = arrays[0]
    return Func(
        array,
        Value(sep),
        Value(null),
        function="array_to_string",
        output_field=models.CharField(),
    )


def limit(string_expr: Union[Expression, Combinable], length: int = LENGTH_LIMIT) -> Func:
    """Shorten the result of the string expression to length `limit`."""
    return Func(string_expr, Value(length), function="left", output_field=models.CharField())


def concatenate(*expr: Union[Expression, Combinable], sep: str = ", ") -> Func:
    """Concatenate the expressions `expr`, separated by `sep`."""
    return Func(Value(sep), *expr, function="concat_ws")


def string_list(path: str, sep: str = ", ", length: int = LENGTH_LIMIT, distinct: bool = True) -> Func:
    """Concatenate the values from `path`, separated by `sep`, up to a length of `length`."""
    return limit(array_to_string(to_array(path, distinct=distinct), sep=sep), length=length)
