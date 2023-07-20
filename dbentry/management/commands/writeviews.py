import inspect

from django.contrib.admin.utils import lookup_field
from django.core.management import BaseCommand

from dbentry.admin import HiddenFromIndex
from dbentry.base.admin import MIZModelAdmin


def write_listviews():
    from dbentry.admin import miz_site

    with open("list_.py", "w") as f:
        f.write("""from dbentry import models as _models
from dbentry.site.registry import register_changelist, ModelType
from dbentry.site.views.base import SearchableListView
from dbentry.utils import add_attrs
from dbentry.utils.text import concat_limit\n
        """)

        model_admin: MIZModelAdmin
        for model_admin in miz_site._registry.values():
            if not isinstance(model_admin, MIZModelAdmin) or isinstance(model_admin, HiddenFromIndex):
                continue
            model = model_admin.model
            ordering = model_admin.ordering
            category = model_admin.index_category.upper()
            list_display = model_admin.list_display
            list_display_links = model_admin.list_display_links
            search_form_kwargs = model_admin.search_form_kwargs
            indent = " "*4
            cls = (
f"""
@register_changelist(_models.{model._meta.object_name}, category=ModelType.{category})
class {model._meta.object_name}List(SearchableListView):    
"""
            )
            f.write(cls)
            attrs = ""
            attrs += f"{indent}model = _models.{model._meta.object_name}\n"
            if ordering:
                attrs += f"{indent}ordering = {ordering}\n"
            if list_display and list_display != ('__str__',):
                attrs += f"{indent}list_display = {list_display}\n"
            if list_display_links:
                attrs += f"{indent}list_display_links = {list_display_links}\n"
            if search_form_kwargs:
                if "forwards" in search_form_kwargs:
                    forwards = search_form_kwargs.pop("forwards")
                    filter_by = {}
                    for dest, source in forwards.items():
                        filter_by[dest] = (source, "TODO: ADD LOOKUP")
                    search_form_kwargs["filter_by"] = filter_by
                attrs += f"{indent}search_form_kwargs = {search_form_kwargs}\n"
            f.write(attrs)
            f.write("\n")

            # Get the 'display' callables
            for name in list_display:
                if name != "__str__" and hasattr(model_admin, name):
                    source: str = "".join(inspect.getsourcelines(getattr(model_admin, name))[0])
                    source = source.replace("@display", "@add_attrs")
                    source = source.replace(" -> str", "")
                    source = source.replace(" -> Union[SafeText, str]", "")
                    f.write(source)
                    f.write("\n")


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        write_listviews()
