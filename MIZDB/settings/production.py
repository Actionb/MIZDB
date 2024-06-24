from .defaults import *  # noqa

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR/MIZDB project dir/settings dir/__file__
BASE_DIR = Path(__file__).resolve().parent.parent.parent

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
DEBUG = False

# URL to the wiki.
# That URL is displayed in the header on each admin page.
# See: sites.MIZAdminSite.each_context
WIKI_URL = os.environ.get("WIKI_URL", "/wiki/Hauptseite")

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
