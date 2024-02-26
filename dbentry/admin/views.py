from typing import Any, Optional

from django.contrib.admin import AdminSite
from django.contrib.auth.mixins import UserPassesTestMixin

from dbentry.admin.site import miz_site


class MIZAdminMixin(object):
    """A mixin that adds admin_site specific context (each_context) to the view."""

    title: str = ""
    site_title: str = "MIZDB"
    breadcrumbs_title: str = ""
    admin_site: AdminSite = miz_site

    def __init__(self, *args: Any, admin_site: Optional[AdminSite] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if admin_site:
            self.admin_site = admin_site

    def get_context_data(self, **kwargs: Any) -> dict:
        context: dict = super().get_context_data(**kwargs)  # type: ignore[misc]

        # Context variables title & site_title for the html document's title.
        # (used by admin/base_site.html)
        if self.title:
            context.setdefault("title", self.title)
        if self.site_title:
            context.setdefault("site_title", self.site_title)
        if self.breadcrumbs_title:
            context.setdefault("breadcrumbs_title", self.breadcrumbs_title)
        # Enable popups behaviour for custom views.
        context["is_popup"] = "_popup" in self.request.GET  # type: ignore[attr-defined]
        # Add the admin site context.
        site_context = self.admin_site.each_context(self.request)  # type: ignore[attr-defined]
        return {**site_context, **context}


class SuperUserOnlyMixin(UserPassesTestMixin):
    """Only allow superusers to access the view."""

    def test_func(self) -> bool:
        """test_func for UserPassesTestMixin."""
        # noinspection PyUnresolvedReferences
        return self.request.user.is_superuser
