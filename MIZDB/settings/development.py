from .defaults import *

DEBUG = True

ALLOWED_HOSTS = [".localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = INSTALLED_APPS + [
    "debug_toolbar",
]

MIDDLEWARE = MIDDLEWARE + [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Required for debug_toolbar:
INTERNAL_IPS = ["127.0.0.1"]
