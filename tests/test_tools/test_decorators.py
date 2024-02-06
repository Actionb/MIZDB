from dbentry.admin.site import MIZAdminSite
from dbentry.tools.decorators import register_tool
from tests.case import MIZTestCase


class TestRegisterToolDecorator(MIZTestCase):

    def test(self):
        """
        Assert that the register_tool decorator calls a site's register_tool
        method with the right arguments and adds the view to the list of tool
        views.
        """
        site = MIZAdminSite()

        @register_tool(
            url_name='url_name',
            index_label='index_label',
            permission_required=('dbentry.ausgabe_add',),
            superuser_only=True,
            site=site
        )
        class DummyView:
            pass

        self.assertIn(
            (DummyView, 'url_name', 'index_label', ('dbentry.ausgabe_add',), True),
            site.tools
        )
