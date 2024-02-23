# from typing import TypeVar, Generic, Union
#
# from django.contrib.auth.mixins import UserPassesTestMixin
# from django.http import HttpResponse
# from django.views import View
# from django.views.generic.base import TemplateResponseMixin, ContextMixin
#
# _ViewT = TypeVar("_ViewT", bound=Union[TemplateResponseMixin, View])
# class _MixinB(ContextMixin, TemplateResponseMixin, View):
#     pass
#
# class SuperUserOnlyMixin(UserPassesTestMixin, _MixinB):
#     bar: str
#
#     def test_func(self) -> bool: ...
#     def foo(self) -> HttpResponse: ...
