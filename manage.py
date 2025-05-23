#!/usr/bin/env python
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    if os.environ.get("DJANGO_DEVELOPMENT"):
        settings_module = "MIZDB.settings.development"
    else:
        if not Path("settings.py").exists():
            print("settings.py not found in root directory.\nHINT: run setup.sh")
            exit(1)
        settings_module = "settings"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django  # noqa: F401
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
