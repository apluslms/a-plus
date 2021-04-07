from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from urllib.parse import urljoin, urlsplit

from course.models import CourseInstance
from inheritance.models import ModelWithInheritance
from lib.helpers import Enum
from lib.models import UrlMixin


def validate_no_domain(value):
    if value and '://' in value:
        raise ValidationError(_("Url can not contain scheme or domain part."))


class LinkService(ModelWithInheritance):
    '''
    A link to an external service.
    '''
    DESTINATION_REGION = Enum([
        ('INTERNAL', 0, _('Destination is hosted internally. Link to internal privacy notice.')),
        ('ORGANIZATION', 1, _('Destination is hosted in the same organization. Link to a privacy notice.')),
        ('EEA', 3, _('Destination is hosted in the European Economic Area. Link to a privacy notice.')),
        ('PRIVACYSHIELD', 5, _('Destination is hosted outside of the European Economic Area and used to be certified under the now invalid EU-US Privacy Shield. Link to an extended privacy notice.')),
        ('GLOBAL', 6, _('Destination is hosted outside of the European Economic Area. Link to an extended privacy notice.')),
    ])
    url = models.CharField(
        max_length=256,
        help_text=_("The service URL")
    )
    destination_region = models.PositiveSmallIntegerField(
        choices=DESTINATION_REGION.choices,
        default=DESTINATION_REGION.GLOBAL,
        help_text=_("The geographical area of the destination. Will display correct user notice."),
    )
    privacy_notice_url = models.CharField(
        max_length=512,
        blank=True,
        help_text=_("A link to the service privacy notice. This is mandatory for services outside organization!"))
    menu_label = models.CharField(
        max_length=255,
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

    def clean(self):
        errors = {}
        if self.destination_region > self.DESTINATION_REGION.ORGANIZATION and not self.privacy_notice_url:
            errors['privacy_notice_url'] = ValidationError(_('Privacy notice URL is mandatory for services outside organization.'))
        if errors:
            raise ValidationError(errors)

    @property
    def url_parts(self):
        return urlsplit(self.url)

    @property
    def method(self):
        return 'GET'

    @property
    def sends_user_info(self):
        return False

    def get_url(self, replace=None, kwargs={}):
        '''Return the URL to the launch page of this service.'''
        if self.destination_region > self.DESTINATION_REGION.INTERNAL:
            return reverse('external-service-link', kwargs=kwargs)
        return self.get_final_url(replace)

    def get_final_url(self, replace=None):
        '''Return the launch URL for this service.

        The optional replace parameter may be a relative URL that is joined to
        the URL path of this service. The relative URL must not include a domain.
        '''
        url = self.url
        if replace:
            assert '://' not in replace and not replace.startswith('//'), "Replace can't include domain"
            url = urljoin(url, replace)
        return url


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

    def __str__(self):
        out = "(LTI) {}: {}".format(self.menu_label, self.url)
        if not self.enabled:
            return "[Disabled] " + out
        return out

    @property
    def method(self):
        return 'POST'

    @property
    def sends_user_info(self):
        return True

    @property
    def is_anonymous(self):
        return self.access_settings == self.LTI_ACCESS.ANON_API_NO

    @property
    def api_access(self):
        return self.access_settings == self.LTI_ACCESS.PUBLIC_API_YES

    def get_url(self, replace=None, kwargs={}):
        return reverse('lti-login', kwargs=kwargs)


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
        on_delete=models.CASCADE,
        related_name="ext_services",
        help_text=_("A course where the menu item exists.")
    )
    access = models.IntegerField(
        choices=ACCESS.choices,
        default=ACCESS.STUDENT,
    )
    service = models.ForeignKey(
        LinkService,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text=_("An external service to link to. These are configured by administrators.")
    )
    menu_url = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        validators=[validate_no_domain],
        help_text=_("""URL that is a) relative to the service URL or b) this course if no service is selected.
Case a: url starting with / overwrites path in service url and extends it otherwise.
case b: url starting with / is absolute within this service and relative to the course path otherwise.
Note that URL entered here can not include scheme or domain.""")
    )
    menu_group_label = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Places menu item under a group label.")
    )
    menu_label = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Label for the menu link (else service default).")
    )
    menu_icon_class = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text=_("Menu icon style name (else service default), e.g. star see https://getbootstrap.com/docs/3.4/components/#glyphicons")
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
        errors = {}
        if not self.service:
            if not self.menu_url:
                errors['menu_url'] = ValidationError(_('Relative URL is required when there is no preconfigured service selected.'))
            if not self.menu_label:
                errors['menu_label'] = ValidationError(_('Menu label is required when there is no preconfigured service selected.'))
        if errors:
            raise ValidationError(errors)

    @cached_property
    def is_enabled(self):
        if self.service:
            return self.service.enabled and self.enabled
        return self.enabled

    @cached_property
    def label(self):
        if self.menu_label:
            return self.menu_label
        if self.service:
            return self.service.menu_label
        return ""

    @cached_property
    def icon_class(self):
        if self.menu_icon_class:
            return self.menu_icon_class
        if self.service:
            return self.service.menu_icon_class
        return ""

    @cached_property
    def url(self):
        if self.service:
            kwargs = {
                "course_slug": self.course_instance.course.url,
                "instance_slug": self.course_instance.url,
                "menu_id": self.id,
            }
            return self.service.as_leaf_class().get_url(replace=self.menu_url, kwargs=kwargs)
        if '://' in self.menu_url:
            # Deprecated, but DB can have old urls
            return self.menu_url
        return urljoin(self.course_instance.get_absolute_url(), self.menu_url)

    @cached_property
    def final_url(self):
        if self.service:
            return self.service.as_leaf_class().get_final_url(self.menu_url)
        else:
            return urljoin(self.course_instance.get_absolute_url(), self.menu_url)

    def get_url_kwargs(self):
        return dict(menu_id=self.id, **self.course_instance.get_url_kwargs())
