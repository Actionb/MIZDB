import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    with open(BASE_DIR / ".secrets" / ".passwd") as f:
        password = f.readline().strip()
except FileNotFoundError as e:
    raise FileNotFoundError(
        "No database password file found. Create a file called '.passwd' "
        "in the '.secrets' subdirectory that contains the database password.\n"
        "HINT: run setup.sh"
    ) from e

SECRET_KEY = 'abcdefghi'

ALWAYS_INSTALLED_APPS = [
    'dbentry.apps.DbentryConfig',
    'dbentry.apps.DbentryAdminConfig',
    'dal',
    'dal_select2',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'formtools',
    'django.contrib.postgres',
    'django_admin_logs',
    'dbentry.site',
    "django_bootstrap5",
    "mizdb_inlines",
    "mizdb_tomselect",
]

TEST_APPS = [
    "tests",
    "tests.test_actions",
    "tests.test_admin_autocomplete",
    "tests.test_admin",
    "tests.test_autocomplete",
    "tests.test_base",
    "tests.test_commands",
    "tests.test_dbentry",
    "tests.test_factory",
    "tests.test_tools",
    "tests.test_search",
    "tests.test_site",
    "tests.test_templatetags",
    "tests.test_utils",
]

INSTALLED_APPS = ALWAYS_INSTALLED_APPS + TEST_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "dbentry.fts.db",
        "NAME": os.environ.get("DB_NAME", "mizdb"),
        "USER": os.environ.get("DB_USER", "mizdb_user"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", 5432),
        "PASSWORD": password,
    },
}

DEBUG = True

ROOT_URLCONF = 'tests.urls'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Add a NullHandler to the root logger for test runs.
# This will stop log messages to be printed to sys.stderr during tests
# if no other handlers are assigned.
# Note that django debug toolbar adds a handler to the root logger that
# handles all log records. The toolbar need not be enabled for this.
logging.getLogger().addHandler(logging.NullHandler())

STATIC_URL = '/static/'

WIKI_URL = 'http://test.wiki.org/'

TIME_ZONE = 'Europe/Berlin'

LANGUAGE_CODE = "de"

LOGIN_URL = 'login'

BOOTSTRAP5 = {
    "field_renderers": {"default": "dbentry.site.renderer.MIZFieldRenderer"},
    "required_css_class": "required",
    "set_placeholder": False
}

ANONYMOUS_CAN_VIEW = True

CSRF_FAILURE_VIEW = "dbentry.csrf.csrf_failure"
