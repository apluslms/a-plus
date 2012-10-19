import os,sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
sys.path.append(os.path.dirname(__file__))

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
