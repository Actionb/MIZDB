"""Settings shared by both production and development environments."""
import logging
import sys
from pathlib import Path

import yaml

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR/MIZDB project dir/settings dir/__file__
BASE_DIR = Path(__file__).resolve().parent.parent.parent

with open(BASE_DIR / 'config.yaml', encoding='utf-8') as f:
    config = yaml.safe_load(f)

SECRET_KEY = config.get('SECRET_KEY', '')

# NOTE: The ServerName declared in the VirtualHost
#   /etc/apache2/sites-available/mizdb.conf must be included:
ALLOWED_HOSTS = config.get('ALLOWED_HOSTS', [])

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'dbentry.fts.db',
        'NAME': config.get('DATABASE_NAME', 'mizdb'),
        'USER': config.get('DATABASE_USER', ''),
        'PASSWORD': config.get('DATABASE_PASSWORD', ''),
        'HOST': config.get('DATABASE_HOST', 'localhost'),
        'PORT': config.get('DATABASE_PORT', ''),
    }
}

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = [
    'dbentry.apps.DbentryConfig',
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'formtools',
    'django.contrib.postgres',
    'django_admin_logs'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'MIZDB.urls'

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

WSGI_APPLICATION = 'MIZDB.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/
LANGUAGE_CODE = 'de'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [BASE_DIR / 'locale']

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'static'

MEDIA_ROOT = BASE_DIR / 'media'

MEDIA_URL = '/media/'

# Override maximum number of post parameters to allow handling of user input during imports
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000

# Avoid having the session cookie expire during work hours by adding 12 hours
# to the default cookie age (2 weeks).
SESSION_COOKIE_AGE = (14 * 24 + 12) * 60 * 60

# URL to the wiki.
# That URL is displayed in the header on each admin page.
# See: sites.MIZAdminSite.each_context
WIKI_URL = config.get('WIKI_URL', '')

# TODO: move this to tests.test_settings - or remove once tests rework is done
if 'test' in sys.argv:
    # Add a NullHandler to the root logger for test runs.
    # This stops log messages to be printed to sys.stderr during tests
    # if no other handlers are assigned.
    # Note that django debug toolbar adds a handler to the root logger that
    # handles all log records. The toolbar need not be enabled for this.
    logging.getLogger().addHandler(logging.NullHandler())
