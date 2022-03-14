from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / 'config.yaml', encoding='utf-8') as f:
    config = yaml.safe_load(f)

SECRET_KEY = 'abcdefghi'

ALWAYS_INSTALLED_APPS = [
    'dbentry',
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
    'django_admin_logs',
]

TEST_APPS = [
    "tests.utils",
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
    'default': {
        'ENGINE': 'dbentry.fts.db',
        'NAME': config.get('DATABASE_NAME', 'mizdb'),
        'USER': config.get('DATABASE_USER', ''),
        'PASSWORD': config.get('DATABASE_PASSWORD', ''),
        'HOST': config.get('DATABASE_HOST', 'localhost'),
        'PORT': config.get('DATABASE_PORT', ''),
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

# DATABASE_ROUTERS = ['tests.dbrouter.SQLiteRouter']

DEBUG = True

ROOT_URLCONF = 'MIZDB.urls'  # TODO: or test urls?

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
