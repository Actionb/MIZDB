import os

if os.environ.get('DJANGO_DEVELOPMENT'):
    from .development import *  # noqa
else:
    from .production import *  # noqa
