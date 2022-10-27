from .defaults import *

import sys  # noqa

DEBUG = True

INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Required for debug_toolbar:
INTERNAL_IPS = ['127.0.0.1']

WIKI_URL = 'http://127.0.0.1/wiki/Hauptseite'
