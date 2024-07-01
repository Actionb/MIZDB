import os

import django
from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import File

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MIZDB.settings.development")
django.setup()


def on_env(env: Environment, config: MkDocsConfig, files: File) -> Environment:
    """Make some django template tags available in the jinja template."""
    # See: https://docs.djangoproject.com/en/dev/topics/templates/#django.template.backends.jinja2.Jinja2
    env.globals.update(
        {
            "static": static,
            "url": reverse,
        }
    )
    return env
