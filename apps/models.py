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
    container_type = models.ForeignKey(ContentType,
        verbose_name=_('LABEL_CONTAINER_TYPE'),
        on_delete=models.CASCADE,
    )
    container_pk = models.TextField(
        verbose_name=_('LABEL_CONTAINER_PK'),
    )
    container = GenericForeignKey(ct_field="container_type", fk_field="container_pk")

    # Apps used to have an oembed reference which was removed in migration to Python 3
    # in favor of future implementations, for example LTI.

    class Meta:
        verbose_name = _('MODEL_NAME_ABSTRACT_APP')
        verbose_name_plural = _('MODEL_NAME_ABSTRACT_APP_PLURAL')
        abstract = True


class BaseTab(AbstractApp):
    label = models.CharField(
        verbose_name=_('LABEL_LABEL'),
        max_length=12,
        help_text=_('TAB_LABEL_HELPTEXT'),
    )
    title = models.CharField(
        verbose_name=_('LABEL_TITLE'),
        max_length=64,
        help_text=_('TAB_TITLE_HELPTEXT'),
    )
    order = models.IntegerField(
        verbose_name=_('LABEL_ORDER'),
        default=100,
    )

    # A Tab can be opened in a new window, in the same window?
    opening_method = models.CharField(
        verbose_name=_('LABEL_OPENING_METHOD'),
        max_length=32,
        blank=True,
    )

    def render(self):
        return _('TAB_NO_CONTENT')

    def get_label(self):
        return self.label

    def get_container(self):
        if isinstance(self.container, ModelWithInheritance):
            return self.container.as_leaf_class()
        return self.container

    def get_renderer_class(self):
        raise NotImplementedError('Missing method implementation!')

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = _('MODEL_NAME_BASE_TAB')
        verbose_name_plural = _('MODEL_NAME_BASE_TAB_PLURAL')
        ordering = ['order', 'id']


class HTMLTab(BaseTab):
    content = models.TextField(
        verbose_name=_('LABEL_CONTENT'),
    )

    def render(self):
        return mark_safe(self.content)

    class Meta:
        verbose_name = _('MODEL_NAME_HTML_TAB')
        verbose_name_plural = _('MODEL_NAME_HTML_TAB_PLURAL')


class ExternalEmbeddedTab(BaseTab):
    content_url = models.URLField(
        verbose_name=_('LABEL_CONTENT_URL'),
        max_length=128,
    )
    element_id = models.CharField(
        verbose_name=_('LABEL_ELEMENT_ID'),
        max_length=32,
        blank=True,
    )

    def get_renderer_class(self):
        return TabRenderer

    class Meta:
        verbose_name = _('MODEL_NAME_EXTERNAL_EMBEDDED_TAB')
        verbose_name_plural = _('MODEL_NAME_EXTERNAL_EMBEDDED_TAB_PLURAL')


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

    content_url = models.URLField(
        verbose_name=_('LABEL_CONTENT_URL'),
        max_length=255,
    )

    # Desired width and height
    width = models.IntegerField(
        verbose_name=_('LABEL_WIDTH'),
    )
    height = models.IntegerField(
        verbose_name=_('LABEL_HEIGHT'),
    )

    def get_renderer_class(self):
        return ExternalIFrameTabRenderer

    class Meta:
        verbose_name = _('MODEL_NAME_EXTERNAL_IFRAME_TAB')
        verbose_name_plural = _('MODEL_NAME_EXTERNAL_IFRAME_TAB_PLURAL')


class BasePlugin(AbstractApp):
    title = models.CharField(
        verbose_name=_('LABEL_TITLE'),
        max_length=64
    )
    views = models.CharField(
        verbose_name=_('LABEL_VIEWS'),
        max_length=255,
        blank=True,
    )

    def render(self):
        leaf = self.as_leaf_class()
        if leaf != self:
            return leaf.render()
        return _('BASE_PLUGIN_MISSING_RENDER-METHOD')

    class Meta:
        verbose_name = _('MODEL_NAME_BASE_PLUGIN')
        verbose_name_plural = _('MODEL_NAME_BASE_PLUGIN_PLURAL')


class RSSPlugin(BasePlugin):
    feed_url = models.URLField(
        verbose_name=_('LABEL_FEED_URL'),
        max_length=256,
        blank=False,
    )

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

    class Meta:
        verbose_name = _('MODEL_NAME_RSS_PLUGIN')
        verbose_name_plural = _('MODEL_NAME_RSS_PLUGIN_PLURAL')


class HTMLPlugin(BasePlugin):
    content = models.TextField(
        verbose_name=_('LABEL_CONTENT'),
        blank=False,
    )

    def render(self):
        return mark_safe(self.content)

    class Meta:
        verbose_name = _('MODEL_NAME_HTML_PLUGIN')
        verbose_name_plural = _('MODEL_NAME_HTML_PLUGIN_PLURAL')


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

    service_url = models.URLField(
        verbose_name=_('LABEL_SERVICE_URL'),
        max_length=255,
    )

    # Desired width and height
    width = models.IntegerField(
        verbose_name=_('LABEL_WIDTH'),
    )
    height = models.IntegerField(
        verbose_name=_('LABEL_HEIGHT'),
    )

    def get_renderer_class(self):
        return ExternalIFramePluginRenderer

    class Meta:
        verbose_name = _('MODEL_NAME_EXTERNAL_IFRAME_PLUGIN')
        verbose_name_plural = _('MODEL_NAME_EXTERNAL_IFRAME_PLUGIN_PLURAL')
