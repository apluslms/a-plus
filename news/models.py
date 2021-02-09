from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from course.models import CourseInstance
from lib.helpers import Enum
from lib.models import UrlMixin


class News(models.Model, UrlMixin):
    AUDIENCE = CourseInstance.ENROLLMENT_AUDIENCE
    course_instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE,
        related_name="news")
    audience = models.IntegerField(choices=AUDIENCE.choices, default=AUDIENCE.ALL_USERS)
    publish = models.DateTimeField(default=timezone.now)
    title = models.CharField(max_length=255)
    body = models.TextField()
    pin = models.BooleanField(default=False)

    class Meta:
        ordering = ['course_instance', '-pin', '-publish']

    def __str__(self):
        return "{} {}".format(str(self.publish), self.title)

    def get_url_kwargs(self):
        return dict(news_id=self.id, **self.course_instance.get_url_kwargs())
