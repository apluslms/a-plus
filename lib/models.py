from django.core.urlresolvers import reverse

class UrlMixin(object):
    def get_url(self, name):
        kwargs = self.get_url_kwargs()
        return reverse(name, kwargs=kwargs)

    def get_absolute_url(self):
        if not hasattr(self, 'ABSOLUTE_URL_NAME'):
            raise NotImplementedError("Model %r doesn't have absolute url" % self)
        return self.get_url(self.ABSOLUTE_URL_NAME)

    def get_edit_url(self):
        if not hasattr(self, 'EDIT_URL_NAME'):
            raise NotImplementedError("Model %r doesn't have absolute url" % self)
        return self.get_url(self.EDIT_URL_NAME)