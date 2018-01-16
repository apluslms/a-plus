from django.conf import settings
from pyrabbit.api import Client
import logging

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


LOGGER = logging.getLogger('main')


# Create rabbitmq management client.
client = None
path = None
if settings.CELERY_BROKER:
    uri = urlparse(settings.CELERY_BROKER)
    client = Client(
        "{}:{:d}".format(uri.hostname, settings.RABBITMQ_MANAGEMENT["port"]),
        uri.username,
        settings.RABBITMQ_MANAGEMENT["password"]
    )
    path = uri.path


def queue_length():
    '''
    Gets the length of the queue.

    @rtype: C{int}
    @return: a number of queued tasks
    '''
    if client:
        try:
            return client.get_queue_depth(path, "celery")
        except Exception:
            LOGGER.exception("Queue length is unknown.")
    return 0
