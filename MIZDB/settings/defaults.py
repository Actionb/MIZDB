"""Settings shared by both production and development environments."""
import logging
import os
import sys

import yaml
# TODO: update django doc refs version 1.11 -> 3.x/2.2

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = (
    os.path.dirname(  # Base directory
        os.path.dirname(  # MIZDB project directory
            os.path.dirname(  # settings directory
                os.path.abspath(__file__)
            )
        )
    )
)
with open(os.path.join(BASE_DIR, 'config.yaml')) as f:
    config = yaml.safe_load(f)

SECRET_KEY = config.get('SECRET_KEY', '')

# NOTE: The ServerName declared in the VirtualHost
#   /etc/apache2/sites-available/mizdb.conf must be included:
ALLOWED_HOSTS = config.get('ALLOWED_HOSTS', [])

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
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
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

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
    'django.contrib.postgres'
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
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/
LANGUAGE_CODE = 'de'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale')
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

MEDIA_URL = '/media/'

# Override maximum number of post parameters to allow handling of user input during imports
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000

# URL to the wiki.
# That URL is displayed in the header on each admin page.
# See: sites.MIZAdminSite.each_context
WIKI_URL = config.get('WIKI_URL', '')

if 'test' in sys.argv:
    # Add a NullHandler to the root logger for test runs.
    # This stops log messages to be printed to sys.stderr during tests
    # if no other handlers are assigned.
    # Note that django debug toolbar adds a handler to the root logger that
    # handles all log records. The toolbar need not be enabled for this.
    logging.getLogger().addHandler(logging.NullHandler())
