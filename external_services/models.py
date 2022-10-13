from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from urllib.parse import urljoin, urlsplit

from course.models import CourseInstance
from inheritance.models import ModelWithInheritance
from lib.fields import DefaultForeignKey
from lib.helpers import Enum
from lib.models import UrlMixin


def validate_no_domain(value):
    if value and '://' in value:
        raise ValidationError(_('URL_CANNOT_CONTAIN_SCHEME_OR_DOMAIN'))


class LinkService(ModelWithInheritance):
    '''
    A link to an external service.
    '''
    DESTINATION_REGION = Enum([
        ('INTERNAL', 0, _('DESTINATION_INTERNAL_PRIVACY_NOTICE')),
        ('ORGANIZATION', 1, _('DESTINATION_ORGANIZATION_PRIVACY_NOTICE')),
        ('EEA', 3, _('DESTINATION_EEA_PRIVACY_NOTICE')),
        ('PRIVACYSHIELD', 5, _('DESTINATION_PRIVACYSHIELD_PRIVACY_NOTICE')),
        ('GLOBAL', 6, _('DESTINATION_GLOBAL_PRIVACY_NOTICE')),
    ])
    url = models.CharField(
        verbose_name=_('LABEL_URL'),
        max_length=256,
        help_text=_('SERVICE_URL')
    )
    destination_region = models.PositiveSmallIntegerField(
        verbose_name=_('LABEL_DESTINATION_REGION'),
        choices=DESTINATION_REGION.choices,
        default=DESTINATION_REGION.GLOBAL,
        help_text=_('SERVICE_DESTINATION_REGION_HELPTEXT'),
    )
    privacy_notice_url = models.CharField(
        verbose_name=_('LABEL_PRIVACY_NOTICE_URL'),
        max_length=512,
        blank=True,
        help_text=_('SERVICE_PRIVACY_NOTICE_URL_HELPTEXT'))
    menu_label = models.CharField(
        verbose_name=_('LABEL_MENU_LABEL'),
        max_length=255,
        help_text=_('SERVICE_MENU_LABEL_HELPTEXT')
    )
    menu_icon_class = models.CharField(
        verbose_name=_('LABEL_MENU_ICON_CLASS'),
        max_length=32,
        default="globe",
        help_text=_('SERVICE_MENU_ICON_HELPTEXT')
    )
    enabled = models.BooleanField(
        verbose_name=_('LABEL_ENABLED'),
        default=True,
        help_text=_('SERVICE_ENABLED_HELPTEXT')
    )

    class Meta:
        verbose_name = _('MODEL_NAME_LINK_SERVICE')
        verbose_name_plural = _('MODEL_NAME_LINK_SERVICE_PLURAL')
        ordering = ["menu_label"]

    def __str__(self):
        out = "{}: {}".format(self.menu_label, self.url)
        if not self.enabled:
            return "[Disabled] " + out
        return out

    def clean(self):
        errors = {}
        if self.destination_region > self.DESTINATION_REGION.ORGANIZATION and not self.privacy_notice_url:
            errors['privacy_notice_url'] = ValidationError(_('SERVICE_ERROR_PRIVACY_NOTICE_URL_MANDATORY'))
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

    def get_url(self, replace=None, kwargs={}): # pylint: disable=dangerous-default-value
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
        ('ANON_API_NO', 0, _('LTI_SERVICE_ANONYMOUS_NO_API')),
        ('PUBLIC_API_NO', 5, _('LTI_SERVICE_PUBLIC_NO_API')),
        ('PUBLIC_API_YES', 10, _('LTI_SERVICE_PUBLIC_YES_API')),
    ])
    access_settings = models.IntegerField(
        verbose_name=_('LABEL_ACCESS_SETTINGS'),
        choices=LTI_ACCESS.choices,
        default=LTI_ACCESS.ANON_API_NO,
        help_text=_('LTI_SERVICE_ACCESS_SETTINGS_HELPTEXT')
    )
    consumer_key = models.CharField(
        verbose_name=_('LABEL_CONSUMER_KEY'),
        max_length=128,
        help_text=_('LTI_SERVICE_CONSUMER_KEY_HELPTEXT')
    )
    consumer_secret = models.CharField(
        verbose_name=_('LABEL_CONSUMER_SECRET'),
        max_length=128,
        help_text=_('LTI_SERVICE_CONSUMER_SECRET_HELPTEXT')
    )

    class Meta:
        verbose_name = _('MODEL_NAME_LTI_SERVICE')
        verbose_name_plural = _('MODEL_NAME_LTI_SERVICE_PLURAL')

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

    def get_url(self, replace=None, kwargs={}): # pylint: disable=dangerous-default-value
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
        ('STUDENT', 0, _('MENU_ITEM_ACCESS_ALL')),
        ('ASSISTANT', 5, _('MENU_ITEM_ACCESS_ASSISTANTS_AND_TEACHERS')),
        ('TEACHER', 10, _('MENU_ITEM_ACCESS_TEACHERS')),
    ])
    course_instance = models.ForeignKey(
        CourseInstance,
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
        related_name="ext_services",
        help_text=_('MENU_ITEM_COURSE_INSTANCE_HELPTEXT')
    )
    access = models.IntegerField(
        verbose_name=_('LABEL_ACCESS'),
        choices=ACCESS.choices,
        default=ACCESS.STUDENT,
    )
    service = DefaultForeignKey(
        LinkService,
        verbose_name=_('LABEL_SERVICE'),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text=_('MENU_ITEM_SERVICE_HELPTEXT')
    )
    menu_url = models.CharField(
        verbose_name=_('LABEL_MENU_URL'),
        max_length=256,
        blank=True,
        null=True,
        help_text=_('MENU_ITEM_MENU_URL_HELPTEXT'""),
        validators=[validate_no_domain],
    )
    menu_group_label = models.CharField(
        verbose_name=_('LABEL_MENU_GROUP_LABEL'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('MENU_ITEM_MENU_GROUP_LABEL_HELPTEXT'),
    )
    menu_label = models.CharField(
        verbose_name=_('LABEL_MENU_LABEL'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('MENU_ITEM_MENU_LINK_LABEL_HELPTEXT'),
    )
    menu_icon_class = models.CharField(
        verbose_name=_('LABEL_MENU_ICON_CLASS'),
        max_length=32,
        null=True,
        blank=True,
        help_text=_('MENU_ITEM_MENU_ICON_CLASS_HELPTEXT'),
    )
    menu_weight = models.IntegerField(
        verbose_name=_('LABEL_MENU_WEIGHT'),
        default=0,
        help_text=_('MENU_ITEM_MENU_WEIGHT_HELPTEXT'),
    )
    enabled = models.BooleanField(
        verbose_name=_('LABEL_ENABLED'),
        default=True,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_MENU_ITEM')
        verbose_name_plural = _('MODEL_NAME_MENU_ITEM_PLURAL')
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
                errors['menu_url'] = ValidationError(_(
                    'MENU_ITEM_ERROR_MENU_URL_REQUIRED_WHEN_NO_PRECONFIGURED_SERVICE_SELECTED'
                ))
            if not self.menu_label:
                errors['menu_label'] = ValidationError(_(
                    'MENU_ITEM_ERROR_MENU_LABEL_REQUIRED_WHEN_NO_PRECONFIGURED_SERVICE_SELECTED'
                ))
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
        return urljoin(self.course_instance.get_absolute_url(), self.menu_url)

    def get_url_kwargs(self):
        return dict(menu_id=self.id, **self.course_instance.get_url_kwargs())
