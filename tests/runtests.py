#!/usr/bin/env python
import os
import sys
from pathlib import Path

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    # sys.path.insert(0, str(Path(os.getcwd()).parent))  # TODO: what is this needed for?
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(keepdb=True)
    failures = test_runner.run_tests(["tests"])
    sys.exit(bool(failures))
