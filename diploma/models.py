import hashlib
import time
from django.db import models
from django.utils.translation import gettext_lazy as _

from course.models import CourseInstance, CourseModule
from exercise.models import BaseExercise
from lib.fields import JSONField
from lib.helpers import safe_file_name
from lib.models import UrlMixin
from userprofile.models import UserProfile


def build_upload_dir(instance, filename):
    return "diploma/{:d}_{}".format(instance.id, safe_file_name(filename))


class CourseDiplomaDesign(models.Model):
    USERGROUP = CourseInstance.ENROLLMENT_AUDIENCE
    course = models.OneToOneField(CourseInstance,
        verbose_name=_('LABEL_COURSE'),
        on_delete=models.SET_NULL,
        null=True,
    )
    availability = models.IntegerField(
        verbose_name=_('LABEL_AVAILABILTY'),
        choices=USERGROUP.choices, default=USERGROUP.EXTERNAL_USERS,
    )
    logo = models.ImageField(
        verbose_name=_('LABEL_LOGO'),
        blank=True, null=True,
        upload_to=build_upload_dir,
    )
    title = models.TextField(
        verbose_name=_('LABEL_TITLE'),
        blank=True,
    )
    body = models.TextField(
        verbose_name=_('LABEL_BODY'),
        blank=True,
    )
    date = models.CharField(
        verbose_name=_('LABEL_DATE'),
        max_length=256,
    )
    signature_name = models.CharField(
        verbose_name=_('LABEL_SIGNATURE_NAME'),
        max_length=256,
        blank=True,
    )
    signature_title = models.CharField(
        verbose_name=_('LABEL_SIGNATURE_TITLE'),
        max_length=256,
        blank=True,
    )
    small_print = models.TextField(
        verbose_name=_('LABEL_SMALL_PRINT'),
        blank=True,
    )
    point_limits = JSONField(
        verbose_name=_('LABEL_POINT_LIMITS'),
        blank=True,
        help_text=_('DIPLOMA_POINT_LIMITS_HELPTEXT'),
    )
    pad_points = models.BooleanField(
        verbose_name=_('LABEL_PAD_POINTS'),
        default=False,
        help_text=_('DIPLOMA_PAD_POINTS_HELPTEXT'),
    )
    exercises_to_pass = models.ManyToManyField(BaseExercise,
        verbose_name=_('LABEL_EXERCISES_TO_PASS'),
        blank=True,
    )
    modules_to_pass = models.ManyToManyField(CourseModule,
        verbose_name=_('LABEL_MODULES_TO_PASS'),
        blank=True,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_COURSE_DIPLOMA_DESIGN')
        verbose_name_plural = _('MODEL_NAME_COURSE_DIPLOMA_DESIGN_PLURAL')

    def __str__(self):
        return "CourseDiplomaDesign {} for {}".format(self.pk, str(self.course))


class StudentDiploma(UrlMixin, models.Model):
    design = models.ForeignKey(CourseDiplomaDesign,
        verbose_name=_('LABEL_DESIGN'),
        on_delete=models.CASCADE,
    )
    profile = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_PROFILE'),
        on_delete=models.SET_NULL,
        null=True,
    )
    created = models.DateTimeField(
        verbose_name=_('LABEL_CREATED'),
        auto_now=True,
    )
    hashkey = models.CharField(
        verbose_name=_('LABEL_HASHKEY'),
        max_length=32,
        unique=True,
    )
    name = models.CharField(
        verbose_name=_('LABEL_NAME'),
        max_length=255,
    )
    grade = models.PositiveIntegerField(
        verbose_name=_('LABEL_GRADE'),
        default=0,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_STUDENT_DIPLOMA')
        verbose_name_plural = _('MODEL_NAME_STUDENT_DIPLOMA_PLURAL')

    def generate_hashkey(self) -> None:
        key = None
        while not key or StudentDiploma.objects.filter(hashkey=key).exists():
            m = hashlib.md5("{:d}-{:d}-{:f}".format(
                self.design.id,
                self.profile.id,
                time.time()
            ).encode('ascii'))
            key = m.hexdigest()
        self.hashkey = key

    ABSOLUTE_URL_NAME = 'diploma-view'

    def get_url_kwargs(self):
        return { 'diploma_hash': self.hashkey }
