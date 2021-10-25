import os

if os.environ.get('DJANGO_DEVELOPMENT') in ('true', 'True', '1'):
    from .development import *  # noqa
else:
    try:
        from .production import *  # noqa
    except ImportError as e:
        raise ImportError("Production settings file 'MIZDB.settings.production.py' missing.") from e
