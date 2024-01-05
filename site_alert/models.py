from django.db import models
from django.utils.translation import gettext_lazy as _

from lib.helpers import Enum


class SiteAlert(models.Model):
    """
    SiteAlert models represents sitewide alerts. There can be a single or
    multiple alerts active simultaneously.
    """
    STATUS = Enum([
        ('ACTIVE', 1, _('ACTIVE')),
        ('REMOVED', 2, _('REMOVED')),
    ])

    alert = models.JSONField(
        verbose_name=_('LABEL_ALERT')
    )
    status = models.IntegerField(
        verbose_name=_('LABEL_STATUS'),
        choices=STATUS.choices,
        default=STATUS.ACTIVE,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_SITEALERT')
        verbose_name_plural = _('MODEL_NAME_SITEALERT_PLURAL')