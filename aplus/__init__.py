from .celery import app as celery_app

__version__ = '1.30.1'
"""The version of the A-plus platform."""
VERSION = __version__

__all__ = ("celery_app",)
