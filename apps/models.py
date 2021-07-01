"""
Plugins and tabs make it possible to customize the behavior and appearance of pages in this
system. Plugins are rendered as small "boxes" on the side of a page, where tabs have their own
pages which can be accessed through a tab-like user interface.

Any model can be related to a Plugin or Tab using a django.contrib.contenttypes.GenericRelation
field and naming AbstractApp fields container_pk & container_type for the link.
"""

import datetime

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.template import loader
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
import feedparser

from apps.app_renderers import ExternalIFramePluginRenderer, \
    ExternalIFrameTabRenderer, TabRenderer
from inheritance.models import ModelWithInheritance


class AbstractApp(ModelWithInheritance):

    # Generic foreign key implementation from Django contenttypes framework.
    container_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    container_pk = models.TextField(_('OBJECT_ID'))
    container = GenericForeignKey(ct_field="container_type", fk_field="container_pk")

    # Apps used to have an oembed reference which was removed in migration to Python 3
    # in favor of future implementations, for example LTI.

    class Meta:
        abstract = True


class BaseTab(AbstractApp):
    label = models.CharField(max_length=12,
        help_text=_('TAB_LABEL_HELPTEXT'))
    title = models.CharField(max_length=64,
        help_text=_('TAB_TITLE_HELPTEXT'))
    order = models.IntegerField(default=100)

    # A Tab can be opened in a new window, in the same window?
    opening_method = models.CharField(max_length=32, blank=True)

    def render(self):
        return _('TAB_NO_CONTENT')

    def get_label(self):
        return self.label

    def get_container(self):
        if isinstance(self.container, ModelWithInheritance):
            return self.container.as_leaf_class()
        else:
            return self.container

    def get_renderer_class(self):
        raise NotImplementedError('Missing method implementation!')

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['order', 'id']


class HTMLTab(BaseTab):
    content = models.TextField()

    def render(self):
        return mark_safe(self.content)


class ExternalEmbeddedTab(BaseTab):
    content_url = models.URLField(max_length=128)
    element_id = models.CharField(max_length=32, blank=True)

    def get_renderer_class(self):
        return TabRenderer


class ExternalIFrameTab(BaseTab):
    """
    An ExternalIFrameTab gets its content from an external url resource through
    an iframe which has the content_url as its src, possibly with additional
    url parameters.

    ExternalIFrameTab uses ExternalIFrameTabRenderer for rendering. Refer to
    its documentation for more information about the available url parameters.

    Iframes' width and height are fixed in the html document flow and thus they
    should be given explicitly and they should be the size of the expected
    content html.
    """

    content_url = models.URLField(max_length=255)

    # Desired width and height
    width = models.IntegerField()
    height = models.IntegerField()

    def get_renderer_class(self):
        return ExternalIFrameTabRenderer


class BasePlugin(AbstractApp):
    title = models.CharField(max_length=64)
    views = models.CharField(max_length=255, blank=True)

    def render(self):
        leaf = self.as_leaf_class()
        if leaf != self:
            return leaf.render()
        else:
            return _('BASE_PLUGIN_MISSING_RENDER-METHOD')


class RSSPlugin(BasePlugin):
    feed_url = models.URLField(max_length=256, blank=False)

    def render(self):
        doc = feedparser.parse(self.feed_url)
        feed = doc.feed

        sorted_entries = sorted(doc["entries"], key=lambda entry: entry.published_parsed)
        sorted_entries.reverse()
        sorted_entries = sorted_entries[:5]

        # Set timestamps in a format that Django knows how to handle in templates
        for entry in sorted_entries:
            entry.django_timestamp = datetime.datetime(*entry.published_parsed[:7])

        out = loader.render_to_string("plugins/rss.html", {
            "entries": sorted_entries,
            "title": self.title,
            "feed": feed,
            "plugin": self
        })
        return out


class HTMLPlugin(BasePlugin):
    content = models.TextField(blank=False)

    def render(self):
        return mark_safe(self.content)


class ExternalIFramePlugin(BasePlugin):
    """
    An ExternalIFramePlugin gets its content from an external url resource
    through an iframe which has the content_url as its src, possibly with
    additional url parameters.

    ExternalIFramePlugin uses ExternalIFramePluginRenderer for rendering. Refer
    to its documentation for more information about the available url
    parameters and its view behaviour.

    Iframes' width and height are fixed in the html document flow and thus they
    should be given explicitly and they should be at least the size of the
    expected content html but at maximum the size available for the plugin in
    each view which varies among the views. The size of the rendered iframe
    will thus be the given width and height but at maximum the width and height
    available in the view.
    """

    service_url = models.URLField(max_length=255)

    # Desired width and height
    width = models.IntegerField()
    height = models.IntegerField()

    def get_renderer_class(self):
        return ExternalIFramePluginRenderer
