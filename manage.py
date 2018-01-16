#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
<<<<<<< HEAD
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aplus.settings")
=======
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grader.settings")
>>>>>>> 6084eaa985868bc28e2c48fd1d9fa2b2462c7ca0

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
