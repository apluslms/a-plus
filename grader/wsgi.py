"""
WSGI config for grader project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grader.settings")

import sys
path = os.path.dirname(os.path.dirname(__file__))
if path not in sys.path:
	sys.path.append(path)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

