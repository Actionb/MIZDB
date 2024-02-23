import sys

if sys.version_info < (3, 10):
    print("Older!")
else:
    print("Newer!")

if TYPE_CHECKING:
    if sys.version_info < (3, 10):
        _Base = forms.Form
    else:
        from typing import TypeAlias
        _Base: TypeAlias = forms.Form
else:
    _Base = object