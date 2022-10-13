#!/usr/bin/env python
import os
import sys
import signal

def sighandler(signum, frame): # pylint: disable=unused-argument
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sighandler)
    signal.signal(signal.SIGINT, sighandler)
    if "test" in sys.argv:
        os.environ.setdefault("APLUS_BASE_URL", "http://localhost")
        os.environ.setdefault("APLUS_LOCAL_SETTINGS", "aplus/local_settings.test.py")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aplus.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
