from typing import TYPE_CHECKING

from django import forms
from django.contrib.admin.helpers import Fieldset
from django.forms import Form

# Hotfix 0.16.1
# if TYPE_CHECKING:  # pragma: no cover
#     # For static type checking purposes, have the mixin extend the concrete
#     # base class that they are designed to be used with.
#     FormMixinBase: TypeAlias = forms.Form
# else:
#     FormMixinBase = object

FormMixinBase = object


class MIZAdminFormMixin(FormMixinBase):
    """A form mixin that adds django admin media and fieldsets."""

    class Media:
        css = {"all": ("admin/css/forms.css",)}

    def __iter__(self) -> Fieldset:
        fieldsets = getattr(self, "fieldsets", [(None, {"fields": list(self.fields.keys())})])
        for name, options in fieldsets:
            yield Fieldset(self, name, **options)

    @property
    def media(self) -> forms.Media:
        # Collect the media needed for all the widgets.
        media = super().media
        # Collect the media needed for all fieldsets.
        # This will add collapse.js if necessary
        # (from django.contrib.admin.options.helpers.Fieldset).
        for fieldset in self.__iter__():
            media += fieldset.media
        return media


class MIZAdminForm(MIZAdminFormMixin, Form):
    pass
