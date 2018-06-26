from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import gettext_lazy as _
import re

from course.models import CourseInstance
from inheritance.models import ModelWithInheritance
from lib.helpers import Enum
from lib.models import UrlMixin


class LinkService(ModelWithInheritance):
    '''
    A link to an external service.
    '''
    url = models.CharField(
        max_length=256,
        help_text=_("The service URL")
    )
    menu_label = models.CharField(
        max_length=32,
        help_text=_("A default label to show in the course menu.")
    )
    menu_icon_class = models.CharField(
        max_length=32,
        default="globe",
        help_text=_("A default menu icon style name, see http://getbootstrap.com/components/#glyphicons-glyphs")
    )
    enabled = models.BooleanField(
        default=True,
        help_text=_("If not enabled, the service is disabled for all course instances.")
    )

    class Meta:
        ordering = ["menu_label"]

    def __str__(self):
        out = "{}: {}".format(self.menu_label, self.url)
        if not self.enabled:
            return "[Disabled] " + out
        return out


class LTIService(LinkService):
    '''
    A provider of an LTI service.
    '''
    LTI_ACCESS = Enum([
        ('ANON_API_NO', 0, _('Anonymous service, no API access')),
        ('PUBLIC_API_NO', 5, _('Public service, no API access')),
        ('PUBLIC_API_YES', 10, _('Public service, allow API access')),
    ])
    access_settings = models.IntegerField(
        choices=LTI_ACCESS.choices,
        default=LTI_ACCESS.ANON_API_NO,
        help_text=_("Select whether to pass pseudonymised user data to the LTI service.<br>Public services can also enable sharing the user's API token and course API URL in the LTI launch request. This grants the LTI tool API access with the user's privileges.")
    )
    consumer_key = models.CharField(
        max_length=128,
        help_text=_("The consumer key provided by the LTI service.")
    )
    consumer_secret = models.CharField(
        max_length=128,
        help_text=_("The consumer secret provided by the LTI service.")
    )
    @property
    def is_anonymous(self):
        return self.access_settings == self.LTI_ACCESS.ANON_API_NO

    @property
    def api_access(self):
        return self.access_settings == self.LTI_ACCESS.PUBLIC_API_YES

class MenuItemManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related(
            'course_instance', 'course_instance__course')


class MenuItem(UrlMixin, models.Model):
    '''
    Attaches link to course menu.
    '''
    ACCESS = Enum([
        ('STUDENT', 0, _("All students, assistants and teachers can access.")),
        ('ASSISTANT', 5, _("Only assistants and teachers can access.")),
        ('TEACHER', 10, _("Only teachers can access.")),
    ])
    course_instance = models.ForeignKey(
        CourseInstance,
        related_name="ext_services",
        help_text=_("A course where the menu item exists.")
    )
    access = models.IntegerField(
        choices=ACCESS.choices,
        default=ACCESS.STUDENT,
    )
    service = models.ForeignKey(
        LinkService,
        blank=True,
        null=True,
        help_text=_("If preconfigured, an external service to link.")
    )
    menu_url = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text=_("A link URL (else service default). Relative URLs are relative to course root.")
    )
    menu_group_label = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text=_("Places menu item under a group label.")
    )
    menu_label = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text=_("Label for the menu link (else service default).")
    )
    menu_icon_class = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text=_("Menu icon style name (else service default), e.g. star see http://getbootstrap.com/components/#glyphicons-glyphs")
    )
    menu_weight = models.IntegerField(
        default=0,
        help_text=_("Heavier menu entries are placed after lighter ones.")
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["course_instance", "menu_weight", "menu_label"]

    def __str__(self):
        out = self.label
        if not self.is_enabled:
            return "[Disabled] " + out
        return out

    def clean(self):
        if not self.service and not (self.menu_url and self.menu_label):
            raise ValidationError(_("Either preconfigured service or custom URL and label needs to be provided."))

    @property
    def is_enabled(self):
        if self.service:
            return self.service.enabled and self.enabled
        return self.enabled

    @property
    def label(self):
        if self.menu_label:
            return self.menu_label
        return self.service.menu_label

    @property
    def icon_class(self):
        if self.menu_icon_class:
            return self.menu_icon_class
        if self.service:
            return self.service.menu_icon_class
        return ""

    @property
    def url(self):
        if self.menu_url:
            if re.search(r"^\w+:\/\/", self.menu_url):
                return self.menu_url
            return "{}{}".format(
                self.course_instance.get_absolute_url(),
                self.menu_url[1:] if self.menu_url.startswith("/") else self.menu_url
            )
        if self.is_lti_service():
            instance = self.course_instance
            return reverse('lti-login', kwargs={
                "course_slug": instance.course.url,
                "instance_slug": instance.url,
                "menu_id": self.id,
            })
        return self.service.url

    def is_lti_service(self):
        if not hasattr(self, '_is_lti'):
            self._is_lti = (self.service
                and isinstance(self.service.as_leaf_class(), LTIService))
        return self._is_lti

    def get_url_kwargs(self):
        return dict(menu_id=self.id, **self.course_instance.get_url_kwargs())
