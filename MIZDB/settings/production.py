from .defaults import *  # noqa
from .defaults import secrets

ALLOWED_HOSTS = secrets["ALLOWED_HOSTS"].split(",")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s - %(name)s - %(message)s'
        },
    },
    'filters': {
        # Do not log dev server auto reloads:
        'not_autoreload': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: record.name != 'django.utils.autoreload'
        }
    },
    'loggers': {},
}
