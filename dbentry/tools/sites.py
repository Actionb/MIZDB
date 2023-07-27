from collections import OrderedDict
from typing import Any, List, Optional, OrderedDict as OrderedDictType, Sequence, ValuesView

from django.contrib import admin
from django.core import checks
from django.http import HttpRequest, HttpResponse
from django.urls import NoReverseMatch, reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache


class IndexToolsSite(admin.AdminSite):
    """
    A django admin site that lists registered tool views in the sidebar of the
    index page.
    """
    index_template = 'tools/index.html'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tools: List[tuple] = []

    def check(self, app_configs: Optional[ValuesView]) -> List[checks.CheckMessage]:
        errors = super().check(app_configs)
        # Check that the registered urls are reversible.
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
        Add the given view to the sites' registered tools. A link to the
        registered view will be displayed in the sidebar of the index page.

        Args:
            view: the tool view
            url_name: the reversible url name of the view
            index_label: the label for the link
            permission_required: permissions required for the link to be
              displayed on the index page
            superuser_only: if True, a link will only be displayed to superusers
        """
        self.tools.append((view, url_name, index_label, permission_required, superuser_only))

    def build_admintools_context(self, request: HttpRequest) -> OrderedDictType[str, str]:
        """
        Return a mapping of url_name: index_label of registered tools, ordered
        by index_label, to be added to the index' context.
        Exclude tool views the user does not have permission for.
        """
        result = OrderedDict()
        # noinspection PyUnresolvedReferences
        user = request.user
        # Walk through the tools sorted by index_label:
        for _tool, url, label, perms, su_only in sorted(self.tools, key=lambda tpl: tpl[2]):
            if su_only and not user.is_superuser:
                continue
            if not user.has_perms(perms):
                continue
            result[url] = label
        return result

    @method_decorator(never_cache)
    def index(self, request: HttpRequest, extra_context: Optional[dict] = None) -> HttpResponse:
        # Add the registered admintools to the index page.
        extra_context = extra_context or {}
        extra_context['admintools'] = self.build_admintools_context(request)
        return super().index(request, extra_context)
