from collections import OrderedDict
from typing import Any, List, Optional, OrderedDict as OrderedDictType, Sequence, ValuesView

from django.core import checks
from django.http import HttpRequest, HttpResponse
from django.urls import NoReverseMatch, reverse
from django.views import View
from django.views.decorators.cache import never_cache


class SiteToolMixin(object):
    """A mixin for a django admin site that lists registered tool views in the sidebar."""

    # TODO: create a separate index.html that includes the admin tools stuff

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tools: List[tuple] = []

    def check(self, app_configs: Optional[ValuesView]) -> List[checks.CheckMessage]:
        errors = super().check(app_configs)
        for tool, url_name, *_ in self.tools:
            try:
                reverse(url_name)
            except NoReverseMatch as e:
                errors.append(
                    checks.Error(
                        str(e),
                        hint="Check register_tool decorator args of %s" % tool,
                        obj="%s admin tools" % self.__class__
                    )
                )
        return errors

    def register_tool(
            self,
            view: View,
            url_name: str,
            index_label: str,
            permission_required: Sequence = (),
            superuser_only: bool = False
    ) -> None:
        """
        Add the given view to the sites' registered tools.

        A registered tool view will have a link to it from the index page.
        The link will be labelled with ``index_label``. The view must be
        reversible using ``url_name``. ``permission_required`` dictates what
        permissions the user will need for the link to be included in the index.
        If ``superuser_only`` is True, the link will only be added for
        superusers.
        """
        self.tools.append((view, url_name, index_label, permission_required, superuser_only))

    def build_admintools_context(self, request: HttpRequest) -> OrderedDictType[str, str]:
        """
        Return a mapping of url_name: index_label of registered tools
        (ordered by index_label) to be added to the index' context.
        """
        result = OrderedDict()
        # Walk through the tools by index_label:
        tools = sorted(self.tools, key=lambda t: t[2])
        for _tool, url_name, index_label, permission_required, superuser_only in tools:
            # noinspection PyUnresolvedReferences
            if superuser_only and not request.user.is_superuser:
                continue
            # TODO: check permissions (do not use resolve(), see commit 0190e654)
            result[url_name] = index_label
        return result

    @never_cache
    def index(self, request: HttpRequest, extra_context: Optional[dict] = None) -> HttpResponse:
        # Add the registered admintools to the index page.
        extra_context = extra_context or {}
        extra_context['admintools'] = self.build_admintools_context(request)
        return super().index(request, extra_context)
