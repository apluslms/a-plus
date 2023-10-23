from .celery import app as celery_app

__version__ = '1.20.3'
"""The version of the A-plus platform."""
VERSION = __version__

__all__ = ("celery_app",)
