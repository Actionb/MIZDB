from .defaults import *  # noqa

import os
from pathlib import Path

from .defaults import BASE_DIR, secrets

ALLOWED_HOSTS = secrets["ALLOWED_HOSTS"].split(",")

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
