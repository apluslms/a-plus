from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from course.models import CourseInstance
from lib.models import UrlMixin


class News(models.Model, UrlMixin):
    AUDIENCE = CourseInstance.ENROLLMENT_AUDIENCE
    course_instance = models.ForeignKey(CourseInstance,
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
        related_name="news",
    )
    audience = models.IntegerField(
        verbose_name=_('LABEL_AUDIENCE'),
        choices=AUDIENCE.choices, default=AUDIENCE.ALL_USERS,
    )
    publish = models.DateTimeField(
        verbose_name=_('LABEL_PUBLISH'),
        default=timezone.now,
    )
    title = models.CharField(
        verbose_name=_('LABEL_TITLE'),
        max_length=255,
    )
    body = models.TextField(
        verbose_name=_('LABEL_BODY'),
    )
    pin = models.BooleanField(
        verbose_name=_('LABEL_PIN'),
        default=False,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_NEWS')
        verbose_name_plural = _('MODEL_NAME_NEWS_PLURAL')
        ordering = ['course_instance', '-pin', '-publish']

    def __str__(self):
        return "{} {}".format(str(self.publish), self.title)

    def get_url_kwargs(self):
        return dict(news_id=self.id, **self.course_instance.get_url_kwargs())
