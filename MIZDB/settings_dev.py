from MIZDB.settings_shared import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS.extend([
    'test_without_migrations',
    'debug_toolbar'
])

# Required for debug_toolbar:
INTERNAL_IPS = ['127.0.0.1']

WIKI_URL = 'http://127.0.0.1/wiki/Hauptseite'
