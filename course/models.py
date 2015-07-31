import logging
import urllib.request, urllib.parse

from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.models import BaseTab, BasePlugin
from lib.fields import PercentField
from userprofile.models import UserProfile


class Course(models.Model):
    """
    Course model represents a course in a university. A course has a name and an
    identification number. It also has a URL which is included in the addresses
    of pages under the course.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    url = models.CharField(unique=True, max_length=255, blank=False,
                       validators=[RegexValidator(regex="^[\w\-\.]*$")],
                       help_text=_("Input an URL identifier for this course."))
    teachers = models.ManyToManyField(UserProfile, related_name="teaching_courses", blank=True)

    def __str__(self):
        return "{} {}".format(self.code, self.name)

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        RESERVED = ("admin", "accounts", "shibboleth", "api",
            "archive", "course", "exercise")
        if self.url in RESERVED:
            raise ValidationError(_("Taken words include: {}").format(
                ", ".join(RESERVED)
            ))

    def is_teacher(self, user):
        return user and user.is_authenticated() and (user.is_superuser or \
            self.teachers.filter(id=user.userprofile.id).exists())

    def get_absolute_url(self):
        return reverse('course-instances', kwargs={
            'course': self.url
        })


class CourseInstanceManager(models.Manager):
    """
    Helpers in CourseInstance.objects
    """

    def get_active(self, user=None):
        qs = self.filter(ending_time__gte=timezone.now())
        if not user or not user.is_authenticated():
            qs = qs.filter(visible_to_students=True)
        elif not user.is_superuser:
            qs = qs.filter(Q(visible_to_students=True)
                           | Q(assistants=user.userprofile)
                           | Q(course__teachers=user.userprofile)
                ).distinct()
        return qs


class CourseInstance(models.Model):
    """
    CourseInstance class represent an instance of a course. A single course may have
    several instances either at the same time or during different years. All instances
    have the same teacher, but teaching assistants and students are connected to individual
    instances.
    """
    instance_name = models.CharField(max_length=255)
    website = models.URLField(max_length=255, blank=True)
    url = models.CharField(max_length=255, blank=False,
            validators=[RegexValidator(regex="^[\w\-\.]*$")],
            help_text="Input an URL identifier for this course instance.")
    starting_time = models.DateTimeField()
    ending_time = models.DateTimeField()
    visible_to_students = models.BooleanField(default=True)
    assistants = models.ManyToManyField(UserProfile, related_name="assisting_courses", blank=True)
    course = models.ForeignKey(Course, related_name="instances")
    plugins = generic.GenericRelation(BasePlugin, object_id_field="container_pk",
                                      content_type_field="container_type")
    tabs = generic.GenericRelation(BaseTab, object_id_field="container_pk",
                                   content_type_field="container_type")
    objects = CourseInstanceManager()

    class Meta:
        unique_together = ("course", "url")

    def __str__(self):
        return "{}: {}".format(str(self.course), self.instance_name)

    def is_assistant(self, user):
        return user and user.is_authenticated() \
            and self.assistants.filter(id=user.userprofile.id).exists()

    def is_teacher(self, user):
        return self.course.is_teacher(user)

    def is_course_staff(self, user):
        return self.is_teacher(user) or self.is_assistant(user)

    def get_course_staff_profiles(self):
        return UserProfile.objects.filter(Q(teaching_courses=self.course) | Q(assisting_courses=self))\
            .distinct()

    def get_student_profiles(self):
        # TODO: enrollment should be designed
        return UserProfile.objects.filter(submissions__exercise__course_module__course_instance=self)\
            .distinct()

    def is_open(self):
        return self.starting_time <= timezone.now() <= self.ending_time

    def is_visible_to(self, user=None):
        if self.visible_to_students:
            return True
        return user and self.is_course_staff(user)

    def has_chapters(self):
        return CourseChapter.objects\
            .filter(course_module__course_instance=self)\
            .count() > 0

    def get_url(self, name):
        return reverse(name, kwargs={
            "course": self.course.url,
            "instance": self.url,
        })

    def get_absolute_url(self):
        return self.get_url("course")

    def get_edit_url(self):
        return self.get_url("course-edit")


class CourseHook(models.Model):
    """
    Provides a hook for a course instance, that is called after a certain
    action. Currently only hook implemented is post-grading, i.e. after a
    student submission has been successfully graded by the external service.

    When a hook is triggered it will do a HTTP POST to a defined URL
    passing along data (e.g. submission id).
    """

    HOOK_CHOICES = (
        ("post-grading", "Post grading"),
    )

    hook_url = models.URLField()
    hook_type = models.CharField(max_length=12, choices=HOOK_CHOICES, default="post-grading")
    course_instance = models.ForeignKey(CourseInstance, related_name="course_hooks")

    def __str__(self):
        return "{} -> {}".format(self.course_instance, self.hook_url)

    def trigger(self, data):
        logger = logging.getLogger("plus.hooks")
        try:
            urllib.request.urlopen(self.hook_url,
                urllib.parse.urlencode(data).encode('utf-8'), timeout=10)
            logger.info("%s posted to %s on %s with %s",
                        self.hook_type, self.hook_url, self.course_instance, data)
        except:
            logger.error("HTTP POST failed on %s hook to %s (%s)",
                         self.hook_type, self.hook_url, self.course_instance)


class CourseModule(models.Model):
    """
    CourseModule objects connect chapters and learning objects to logical sets
    of each other and course instances. They also contain information about the
    opening times and deadlines for exercises.
    """
    order = models.IntegerField(default=1)
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255,
                       validators=[RegexValidator(regex="^[\w\-\.]*$")],
                       help_text=_("Input an URL identifier for this module."))
    points_to_pass = models.PositiveIntegerField(default=0)
    introduction = models.TextField(blank=True)
    course_instance = models.ForeignKey(CourseInstance, related_name="course_modules")
    opening_time = models.DateTimeField(default=timezone.now)
    closing_time = models.DateTimeField(default=timezone.now)

    # early_submissions_allowed= models.BooleanField(default=False)
    # early_submissions_start = models.DateTimeField(default=timezone.now, blank=True, null=True)
    # early_submission_bonus  = PercentField(default=0.1,
    #   help_text=_("Multiplier of points to reward, as decimal. 0.1 = 10%"))

    late_submissions_allowed = models.BooleanField(default=False)
    late_submission_deadline = models.DateTimeField(default=timezone.now)
    late_submission_penalty = PercentField(default=0.5,
        help_text=_("Multiplier of points to reduce, as decimal. 0.1 = 10%"))

    class Meta:
        unique_together = ("course_instance", "url")
        ordering = ['closing_time', 'order', 'id']

    def __str__(self):
        if self.order > 0:
            return "{:d}. {}".format(self.order, self.name)
        return self.name

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        RESERVED = ("teachers", "user", "exercises", "apps", "lti-login")
        if self.url in RESERVED:
            raise ValidationError(_("Taken words include: {}").format(
                ", ".join(RESERVED)
            ))

    def is_open(self, when=None):
        when = when or timezone.now()
        return self.opening_time <= when <= self.closing_time

    def is_after_open(self, when=None):
        """
        Checks if current time is past the round opening time.
        """
        when = when or timezone.now()
        return self.opening_time <= when

    def is_late_submission_open(self, when=None):
        when = when or timezone.now()
        return self.late_submissions_allowed \
            and self.closing_time <= when <= self.late_submission_deadline

    def get_late_submission_point_worth(self):
        """
        Returns the percentage (0-100) that late submission points are worth.
        """
        point_worth = 0
        if self.late_submissions_allowed:
            point_worth = int((1.0 - self.late_submission_penalty) * 100.0)
        return point_worth

    def next_module(self):
        return self.course_instance.course_modules \
            .exclude(id=self.id).filter(order__gt=self.order).first()

    def previous_module(self):
        return self.course_instance.course_modules \
            .exclude(id=self.id).filter(order__lt=self.order).last()

    def next(self):
        chapter = self.chapters.first()
        return chapter or self.next_module()

    def previous(self):
        module = self.previous_module()
        chapter = module.chapters.last() if module else None
        return chapter or module

    def get_absolute_url(self):
        instance = self.course_instance
        return reverse('module', kwargs={
            'course': instance.course.url,
            'instance': instance.url,
            'module': self.url,
        })


class CourseChapter(models.Model):
    """
    Chapters can offer and organize learning material as one page chapters.
    """
    course_module = models.ForeignKey(CourseModule, related_name="chapters")
    order = models.IntegerField(default=1)
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255,
        validators=[RegexValidator(regex="^[\w\-\.]*$")],
        help_text=_("Input an URL identifier for this chapter."))
    content_url = models.URLField(help_text=_("The resource to show."))

    class Meta:
        unique_together = ("course_module", "url")
        ordering = ['course_module', 'order', 'id']

    def __str__(self):
        if self.course_module.order > 0:
            return "{:d}.{:d} {}".format(
                self.course_module.order, self.order, self.name)
        return self.name

    @property
    def course_instance(self):
        return self.course_module.course_instance

    def is_after_open(self, when=None):
        return self.course_module.is_after_open(when=when)

    def next(self):
        chapter = self.course_module.chapters \
            .exclude(id=self.id).filter(order__gt=self.order).first()
        return chapter or self.course_module.next_module()

    def previous(self):
        chapter = self.course_module.chapters \
            .exclude(id=self.id).filter(order__lt=self.order).last()
        return chapter or self.course_module

    def get_absolute_url(self):
        module = self.course_module
        instance = module.course_instance
        return reverse('chapter', kwargs={
            'course': instance.course.url,
            'instance': instance.url,
            'module': module.url,
            'chapter': self.url,
        })


class LearningObjectCategory(models.Model):
    """
    Learning objects may be grouped to different categories.
    """
    name = models.CharField(max_length=35)
    description = models.TextField(blank=True)
    points_to_pass = models.PositiveIntegerField(default=0)
    course_instance = models.ForeignKey(CourseInstance, related_name="categories")
    hidden_to = models.ManyToManyField(UserProfile, related_name="hidden_categories",
        blank=True, null=True)

    class Meta:
        unique_together = ("name", "course_instance")

    def __str__(self):
        return self.name

    def is_hidden_to(self, user_profile):
        return self.hidden_to.filter(id=user_profile.id).exists()

    def set_hidden_to(self, user_profile, hide=True):
        if hide and not self.is_hidden_to(user_profile):
            self.hidden_to.add(user_profile)
        elif not hide and self.is_hidden_to(user_profile):
            self.hidden_to.remove(user_profile)
