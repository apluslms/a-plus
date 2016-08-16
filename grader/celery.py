'''
An asychronous grading task that is queued and later run by queue workers.
Requires running Celery which requires running broker e.g. RabbitMQ.
'''
import os

# Set Django configuration path for celeryd.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grader.settings')

from celery import Celery
from django.conf import settings
from access.config import ConfigError


# Check settings object and validate base dir.
if len(settings.BASE_DIR) < 2:
    raise ConfigError("Configuration problem, BASE_DIR: %s", settings.BASE_DIR)

# Create and configure Celery instance.
app = Celery("tasks", broker=settings.CELERY_BROKER)
app.conf.update(
    CELERYD_TASK_TIME_LIMIT=settings.CELERY_TASK_KILL_SEC,
    CELERYD_TASK_SOFT_TIME_LIMIT=settings.CELERY_TASK_LIMIT_SEC,
    #CELERYD_CONCURRENCY=1,
    CELERYD_PREFETCH_MULTIPLIER=1,
    CELERYD_HIJACK_ROOT_LOGGER=True,
    CELERY_ACCEPT_CONTENT = ['json'],
    CELERY_TASK_SERIALIZER = 'json',
    CELERY_RESULT_SERIALIZER = 'json',
)
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
