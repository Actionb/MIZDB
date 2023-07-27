from typing import Dict, Tuple

from django.contrib.postgres.search import SearchVectorField as DjangoSearchVectorField
from dataclasses import dataclass

from django.utils.encoding import force_str


@dataclass
class WeightedColumn:

    name: str
    weight: str
    config: str

    def deconstruct(self) -> Tuple[str, list, Dict[str, list]]:
        """
        Return a 3-tuple (path, args, kwargs) with which the column can be
        recreated.
        """
        return (
            f"dbentry.fts.fields.{self.__class__.__name__}",
            [force_str(self.name), force_str(self.weight), force_str(self.config)],
            {}
        )


class SearchVectorField(DjangoSearchVectorField):

    def __init__(self, *args, columns=None, **kwargs):
        kwargs["null"] = True
        kwargs["blank"] = True
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)
        self.columns = columns

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['columns'] = self.columns
        return name, f"dbentry.fts.fields.{self.__class__.__name__}", args, kwargs
