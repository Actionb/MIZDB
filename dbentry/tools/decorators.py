from typing import Callable, Sequence

from django.views import View

from dbentry.admin.site import MIZAdminSite, miz_site


def register_tool(
    url_name: str,
    index_label: str,
    permission_required: Sequence = (),
    superuser_only: bool = False,
    site: MIZAdminSite = miz_site,
) -> Callable:
    """
    Decorator that registers a view class as a 'tool view' for the given site.

    A link to the registered view will be displayed in the sidebar of the index
    page.

    Args:
        url_name (str): name of the URL pattern to the view
        index_label (str): the label for the link on the index page to the view
        permission_required (Sequence): a sequence of permission codenames
          required to access the view. Used to decide whether to display a link
          to the decorated view on the index page for the current user.
        superuser_only (bool): If True, only superusers will see a link on the
          index page. This does not restrict access to the view in any way.
        site (MIZAdminSite instance): the site to _register the view with
    """

    def decorator(tool_view: View) -> View:
        site.register_tool(tool_view, url_name, index_label, permission_required, superuser_only)
        return tool_view

    return decorator
