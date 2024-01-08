from .defaults import *  # noqa

try:
    with open(BASE_DIR / ".secrets" / ".allowedhosts") as f:
        ALLOWED_HOSTS = f.readline().strip().split(",")
except FileNotFoundError as e:
    raise FileNotFoundError(
        "No allowed hosts file found. Create a file called '.allowedhosts' "
        "in the '.secrets' subdirectory that contains a list of allowed "
        "host names.\n"
        "HINT: run setup.sh"
    ) from e

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Log CSRF failures:
CSRF_FAILURE_VIEW = 'dbentry.csrf.csrf_failure'

# URL to the wiki.
# That URL is displayed in the header on each admin page.
# See: sites.MIZAdminSite.each_context
WIKI_URL = os.environ.get('WIKI_URL') or "/wiki/Hauptseite"

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
            'delay': True,
        },
        'change_confirmation': {
            'class': 'logging.FileHandler',
            'level': 'INFO',
            'filename': '/var/log/mizdb/change_confirmation.log',
            'formatter': 'default',
            'filters': ['not_autoreload'],
            'delay': True,
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
