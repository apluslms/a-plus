import logging
import traceback
from django.db.models.query_utils import DeferredAttribute
from django.urls import reverse


class UrlMixin:
    def get_url(self, name, **add_kwargs):
        kwargs = self.get_url_kwargs()
        kwargs.update(add_kwargs)
        return reverse(name, kwargs=kwargs)

    def get_display_url(self):
        return self.get_absolute_url()

    def get_absolute_url(self):
        if not hasattr(self, 'ABSOLUTE_URL_NAME'):
            raise NotImplementedError("Model %r doesn't have absolute url" % self)
        return self.get_url(self.ABSOLUTE_URL_NAME)

    def get_edit_url(self):
        if not hasattr(self, 'EDIT_URL_NAME'):
            raise NotImplementedError("Model %r doesn't have absolute url" % self)
        return self.get_url(self.EDIT_URL_NAME)


def install_defer_logger():
    logger = logging.getLogger('django.db.deferred')
    orig_get = DeferredAttribute.__get__

    logger.warning("Installing logger for deferred model fields...")

    def get(self, instance, cls=None):
        if instance is None:
            return self
        if self.field.attname not in instance.__dict__:
            filename, linenum, funcname, command = tuple(traceback.extract_stack()[-2])
            logger.warning(
                "Resolving deferred: %s.%s in %s, line %s, func %s: %s",
                instance.__class__.__name__,
                self.field.attname,
                filename,
                linenum,
                funcname,
                command
            )
        return orig_get(self, instance, cls=cls)
    DeferredAttribute.__get__ = get
