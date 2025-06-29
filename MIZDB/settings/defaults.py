"""Settings shared by both production and development environments."""

import os
from pathlib import Path


# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR/MIZDB project dir/settings dir/__file__
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "mizdb")

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "dbentry.fts.db",
        "NAME": os.environ.get("DB_NAME", "mizdb"),
        "USER": os.environ.get("DB_USER", "mizdb_user"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", 5432),
        "PASSWORD": os.environ.get("DB_PASSWORD", "mizdb"),
    }
}

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# Application definition
INSTALLED_APPS = [
    "dbentry.admin.autocomplete.jquery_351",  # see dbentry.admin.autocomplete.jquery_351.README for details
    "dbentry.apps.DbentryConfig",
    "dbentry.apps.DbentryAdminConfig",
    "dal",
    "dal_select2",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "formtools",
    "django.contrib.postgres",
    "django_admin_logs",
    "mizdb_tomselect",
    "mod_wsgi.server",
    "dbentry.site",  # required for finding dbentry/site/static files
    "django_bootstrap5",
    "mizdb_inlines",
    "mizdb_watchlist",
    "import_export",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "MIZDB.urls"

LOGIN_URL = "login"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "MIZDB.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/
LANGUAGE_CODE = "de"

TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_URL = "/static/"

STATIC_ROOT = "static/"

MEDIA_ROOT = BASE_DIR / "media"

MEDIA_URL = "/media/"

# Avoid having the session cookie expire during work hours by adding 12 hours
# to the default cookie age (2 weeks).
SESSION_COOKIE_AGE = (14 * 24 + 12) * 60 * 60

BOOTSTRAP5 = {
    "field_renderers": {"default": "dbentry.site.renderer.MIZFieldRenderer"},
    "required_css_class": "required",
    "set_placeholder": False,
}

# Whether anonymous users can view pages as if they had 'view' permission.
ANONYMOUS_CAN_VIEW = True

# Log CSRF failures:
CSRF_FAILURE_VIEW = "dbentry.csrf.csrf_failure"

STATICFILES_DIRS = [
    BASE_DIR / "docs" / "docs",  # include static files for help pages, such as images
]

ONLINE_HELP_URL = os.environ.get("MIZDB_ONLINE_HELP", "https://actionb.github.io/MIZDB/")
