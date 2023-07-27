from .defaults import *  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Log CSRF failures:
CSRF_FAILURE_VIEW = 'dbentry.csrf.csrf_failure'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'csrf': {
            'class': 'logging.FileHandler',
            'level': 'INFO',
            'filename': '/var/log/mizdb/csrf.log',
            'formatter': 'default',
            'filters': ['not_autoreload'],
        },
        'change_confirmation': {
            'class': 'logging.FileHandler',
            'level': 'INFO',
            'filename': '/var/log/mizdb/change_confirmation.log',
            'formatter': 'default',
            'filters': ['not_autoreload'],
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
    'loggers': {
        'dbentry.csrf': {
            'handlers': ['csrf'],
            'level': 'INFO',
            'propagate': True,
        },
        'change_confirmation': {
            'handlers': ['change_confirmation'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
