from typing import TYPE_CHECKING, TypeVar, Generic

from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.base import ContextMixin, TemplateResponseMixin, View

if TYPE_CHECKING:
    class _MixinBase(ContextMixin, TemplateResponseMixin, View):
        pass
else:
    _MixinBase = object

_MixinB = TypeVar("_MixinB", bound="_MixinBase")


class SuperUserOnlyMixin(UserPassesTestMixin, _MixinBase):
    """Only allow superusers to access the view."""
    bar = ""

    def test_func(self):
        """test_func for UserPassesTestMixin."""
        # Ignore mypy error about user not having is_superuser attribute
        # https://github.com/typeddjango/django-stubs/issues/1058
        return self.request.user.is_superuser  # type: ignore[union-attr]

    def foo(self):
        x = 1 + self.bar
        return self.render_to_response(self.get_context_data(foo=self.bar))
