from .defaults import *  # noqa

import os
from pathlib import Path

from .defaults import BASE_DIR

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "*").split(",")]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "timed_rotating_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": os.getenv("MIZDB_LOG_LEVEL", "INFO"),
            "filename": Path(os.getenv("LOG_DIR", BASE_DIR)) / "mizdb.log",
            "formatter": "default",
            "delay": True,
            "when": "W0",  # rollover every Monday (Weekday 0)
            "backupCount": 12,  # keep 12 weeks worth of logs
        },
    },
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"},
    },
    "filters": {
        # Do not log dev server auto reloads:
        "not_autoreload": {
            "()": "django.utils.log.CallbackFilter",
            "callback": lambda record: record.name != "django.utils.autoreload",
        }
    },
    "loggers": {},
}

# The env var ADMINS is a comma-separated list of admin email-addresses. Split
# this list into 2-tuples.
ADMINS = [(email.strip(), email.strip()) for email in os.getenv("ADMINS", "").split(",")]

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.ionos.de")
EMAIL_PORT = os.getenv("EMAIL_PORT", 465)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "false").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
SERVER_EMAIL = os.getenv("SERVER_EMAIL", EMAIL_HOST_USER)
