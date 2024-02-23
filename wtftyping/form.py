from typing import TYPE_CHECKING
from typing_extensions import TypeAlias

from django import forms

if TYPE_CHECKING:
    # class _Form(forms.Form):
    #     pass
    # _Base = _Form
    _Base: TypeAlias = forms.Form
else:
    _Base = object


class SuffixFormMixin(_Base):
    suffix: str

    def add_suffix(self, field_name: str) -> str:
        return f"{self.prefix}__{field_name}__{self.suffix}"
