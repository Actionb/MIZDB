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
