import datetime
import logging
import urllib.request, urllib.parse

from django.contrib import messages
from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q, Count
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.models import BaseTab, BasePlugin
from lib.email_messages import email_course_error
from lib.fields import PercentField
from lib.helpers import safe_file_name, resize_image, roman_numeral, get_random_string
from lib.remote_page import RemotePage, RemotePageException
from lib.models import UrlMixin
from userprofile.models import UserProfile
from .tree import ModuleTree

logger = logging.getLogger("course.models")


class Course(UrlMixin, models.Model):
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
    teachers = models.ManyToManyField(UserProfile,
        related_name="teaching_courses", blank=True)

    def __str__(self):
        return "{} {}".format(self.code, self.name)

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        RESERVED = ("admin", "accounts", "shibboleth", "api",
            "archive", "course", "exercise")
        if self.url in RESERVED:
            raise ValidationError({
                'url':_("Taken words include: {}").format(
                    ", ".join(RESERVED))
            })

    def is_teacher(self, user):
        return user and user.is_authenticated() and (user.is_superuser or \
            self.teachers.filter(id=user.userprofile.id).exists())


    ABSOLUTE_URL_NAME = "course-instances"

    def get_url_kwargs(self):
        return dict(course_slug=self.url)


class StudentGroup(models.Model):
    """
    Stores a user group for a course instance.
    """
    course_instance = models.ForeignKey('CourseInstance', related_name='groups')
    members = models.ManyToManyField(UserProfile, related_name='groups')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course_instance','timestamp']

    @classmethod
    def get_exact(cls, course_instance, member_profiles):
        qs = cls.objects.filter(course_instance=course_instance) \
            .annotate(count=Count('members')).filter(count=len(member_profiles))
        for profile in member_profiles:
            qs.filter(members=profile)
        return qs.first()

    def equals(self, profiles):
        return set(self.members.all()) == set(profiles)

    def collaborators_of(self, profile):
        return [p for p in self.members.all() if p != profile]


class Enrollment(models.Model):
    """
    Maps an enrolled student in a course instance.
    """
    course_instance = models.ForeignKey('CourseInstance', on_delete=models.CASCADE)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    personal_code = models.CharField(max_length=10, blank=True, default='')
    selected_group = models.ForeignKey(StudentGroup, blank=True, null=True, default=None, on_delete=models.SET_NULL)


def create_enrollment_code(sender, instance, created, **kwargs):
    if created:
        easychars = '0123456789ABCDEFGHJKLMNPQRSTUVXYZ'
        code = get_random_string(6, easychars)
        while Enrollment.objects.filter(course_instance=instance.course_instance, personal_code=code).exists():
            code = get_random_string(6, easychars)
        instance.personal_code = code
        instance.save()

post_save.connect(create_enrollment_code, sender=Enrollment)


class CourseInstanceManager(models.Manager):
    """
    Helpers in CourseInstance.objects
    """

    def get_queryset(self):
        return super().get_queryset().select_related('course').order_by('-starting_time')

    def get_enrolled(self, user=None, end_after=None):
        if not user or not user.is_authenticated():
            return self.none()
        qs = self.filter(visible_to_students=True, students=user.userprofile)
        if not end_after is None:
            qs.exclude(ending_time__lt=end_after)
        return qs

    def get_on_staff(self, user=None, end_after=None):
        if not user or not user.is_authenticated():
            return self.none()
        qs = self.filter(Q(assistants=user.userprofile) |
            Q(course__teachers=user.userprofile)).distinct()
        if not end_after is None:
            qs.exclude(ending_time__lt=end_after)
        return qs

    def get_visible(self, user=None):
        if not user or not user.is_authenticated():
            return self.filter(visible_to_students=True)
        if not user.is_superuser:
            return self.filter(Q(visible_to_students=True)
                           | Q(assistants=user.userprofile)
                           | Q(course__teachers=user.userprofile)
                ).distinct()
        return self.all()


def build_upload_dir(instance, filename):
    """
    Returns the path to a directory where the instance image should be saved.
    """
    return "public/course_instance_{:d}/{}".format(
        instance.id,
        safe_file_name(filename)
    )


class CourseInstance(UrlMixin, models.Model):
    """
    CourseInstance class represent an instance of a course. A single course may have
    several instances either at the same time or during different years. All instances
    have the same teacher, but teaching assistants and students are connected to individual
    instances.
    """
    course = models.ForeignKey(Course, related_name="instances")
    instance_name = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=False,
        validators=[RegexValidator(regex="^[\w\-\.]*$")],
        help_text=_("Input an URL identifier for this course instance."))
    visible_to_students = models.BooleanField(default=True)
    enrollment_audience = models.IntegerField(choices=(
        (1, _('Internal users')),
        (2, _('External users')),
        (3, _('Internal and external users')),
    ), default=1)
    view_content_to = models.IntegerField(choices=(
        (1, _('Enrolled students')),
        (2, _('Enrollment audience')),
        (3, _('All registered users')),
        (4, _('Public to internet')),
    ), default=2)
    starting_time = models.DateTimeField()
    ending_time = models.DateTimeField()
    enrollment_starting_time = models.DateTimeField(blank=True, null=True)
    enrollment_ending_time = models.DateTimeField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True, upload_to=build_upload_dir)
    language = models.CharField(max_length=5, blank=True, default="")
    description = models.TextField(blank=True)
    footer = models.TextField(blank=True)
    index_mode = models.IntegerField(choices=(
        (0, _('User results')),
        (1, _('Table of contents')),
    ), default=0, help_text=_('Select content for the course index page.'))
    module_numbering = models.IntegerField(choices=(
        (0, _("No numbering")),
        (1, _("Arabic")),
        (2, _("Roman")),
        (3, _("Hidden arabic")),
    ), default=1)
    content_numbering = models.IntegerField(choices=(
        (0, _("No numbering")),
        (1, _("Arabic")),
        (2, _("Roman")),
    ), default=1)
    head_urls = models.TextField(blank=True,
        help_text=_("External CSS and JS resources "
            "that are included on all course pages. "
            "Separate with white space."))
    configure_url = models.URLField(blank=True)
    technical_error_emails = models.CharField(max_length=255, blank=True,
        help_text=_("By default exercise errors are reported to teacher "
            "email addresses. Set this field as comma separated emails to "
            "override the recipients."))
    plugins = generic.GenericRelation(BasePlugin, object_id_field="container_pk",
                                      content_type_field="container_type")
    tabs = generic.GenericRelation(BaseTab, object_id_field="container_pk",
                                   content_type_field="container_type")

    assistants = models.ManyToManyField(UserProfile, related_name="assisting_courses", blank=True)
    students = models.ManyToManyField(UserProfile, related_name="enrolled", blank=True, through='Enrollment')
    # categories from course.models.LearningObjectCategory
    # course_modules from course.models.CourseModule

    objects = CourseInstanceManager()
    class Meta:
        unique_together = ("course", "url")

    def __str__(self):
        return "{}: {}".format(str(self.course), self.instance_name)

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        if self.ending_time <= self.starting_time:
            raise ValidationError({
                'ending_time': _("Ending time must be later than starting time.")
            })

    def save(self, *args, **kwargs):
        """
        Saves the model.
        """
        super().save(*args, **kwargs)
        if self.image:
            resize_image(self.image.path, (800,600))

    def is_assistant(self, user):
        return user and user.is_authenticated() \
            and self.assistants.filter(id=user.userprofile.id).exists()

    def is_teacher(self, user):
        return self.course.is_teacher(user)

    def is_course_staff(self, user):
        return self.is_teacher(user) or self.is_assistant(user)

    def is_student(self, user):
        return user and user.is_authenticated() \
            and self.students.filter(id=user.userprofile.id).exists()

    def is_enrollable(self, user):
        if user and user.is_authenticated():
            if self.enrollment_audience == 1:
                return not user.userprofile.is_external
            if self.enrollment_audience == 2:
                return user.userprofile.is_external
            return True
        return False

    def enroll_student(self, user):
        if user and user.is_authenticated() and not self.is_course_staff(user):
            Enrollment.objects.create(course_instance=self, user_profile=user.userprofile)

    def get_enrollment_for(self, user):
        return Enrollment.objects.filter(course_instance=self, user_profile=user.userprofile).first()

    def get_course_staff_profiles(self):
        return UserProfile.objects.filter(Q(teaching_courses=self.course) | Q(assisting_courses=self))\
            .distinct()

    def get_student_profiles(self):
        return self.students.all()

    def get_submitted_profiles(self):
        return UserProfile.objects.filter(submissions__exercise__course_module__course_instance=self)\
            .distinct()\
            .exclude(assisting_courses=self)\
            .exclude(teaching_courses=self.course)

    def is_open(self):
        return self.starting_time <= timezone.now() <= self.ending_time

    @property
    def enrollment_start(self):
        return self.enrollment_starting_time or self.starting_time

    @property
    def enrollment_end(self):
        return self.enrollment_ending_time or self.ending_time

    def is_enrollment_open(self):
        return self.enrollment_start <= timezone.now() <= self.enrollment_end

    def is_visible_to(self, user=None):
        if self.visible_to_students:
            return True
        return user and self.is_course_staff(user)

    @property
    def head_css_urls(self):
        return [url for url in self.head_urls.split() if url.endswith(".css")]

    @property
    def head_js_urls(self):
        return [url for url in self.head_urls.split() if url.endswith(".js")]

    ABSOLUTE_URL_NAME = "course"
    EDIT_URL_NAME = "course-edit"

    def get_url_kwargs(self):
        # dict(foo=bar, **baz()) is not nice, but it's cleanest solution for this
        # specific problem. For more read out stackoverflow answer about merging
        # python dicts in single line: http://stackoverflow.com/a/26853961
        return dict(instance_slug=self.url, **self.course.get_url_kwargs())


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


class CourseModuleManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related(
            'course_instance', 'course_instance__course')


class CourseModule(UrlMixin, models.Model):
    """
    CourseModule objects connect chapters and learning objects to logical sets
    of each other and course instances. They also contain information about the
    opening times and deadlines for exercises.
    """
    STATUS_READY = 'ready'
    STATUS_HIDDEN = 'hidden'
    STATUS_MAINTENANCE = 'maintenance'
    STATUS_CHOICES = (
        (STATUS_READY, _("Ready")),
        (STATUS_HIDDEN, _("Hidden")),
        (STATUS_MAINTENANCE, _("Maintenance")),
    )
    status = models.CharField(max_length=32,
        choices=STATUS_CHOICES, default=STATUS_READY)
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

    objects = CourseModuleManager()

    class Meta:
        unique_together = ("course_instance", "url")
        ordering = ['order', 'closing_time', 'id']

    def __str__(self):
        if self.order > 0:
            if self.course_instance.module_numbering == 1:
                return "{:d}. {}".format(self.order, self.name)
            elif self.course_instance.module_numbering == 2:
                return "{} {}".format(roman_numeral(self.order), self.name)
        return self.name

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        RESERVED = ("teachers", "user", "exercises", "apps", "lti-login")
        if self.url in RESERVED:
            raise ValidationError({
                'url':_("Taken words include: {}").format(", ".join(RESERVED))
            })

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
        return self.course_instance.course_modules\
            .exclude(status='hidden').filter(order__gt=self.order).first()

    def previous_module(self):
        return self.course_instance.course_modules\
            .exclude(status='hidden').filter(order__lt=self.order).last()

    def _children(self):
        if not hasattr(self, '_module_children'):
            self._module_children = ModuleTree(self)
        return self._module_children

    def next(self):
        return self._children().first() or self.next_module()

    def previous(self):
        module = self.previous_module()
        return module._children().last() if module else None

    def flat_learning_objects(self, with_sub_markers=True):
        return self._children().flat(None, with_sub_markers)

    def flat_admin_learning_objects(self, with_sub_markers=True):
        return self._children().flat(None, with_sub_markers, True)


    ABSOLUTE_URL_NAME = "module"

    def get_url_kwargs(self):
        return dict(module_slug=self.url, **self.course_instance.get_url_kwargs())


class LearningObjectCategory(models.Model):
    """
    Learning objects may be grouped to different categories.
    """
    STATUS_READY = 'ready'
    STATUS_HIDDEN = 'hidden'
    STATUS_CHOICES = (
        (STATUS_READY, _("Ready")),
        (STATUS_HIDDEN, _("Hidden")),
    )
    status = models.CharField(max_length=32,
        choices=STATUS_CHOICES, default=STATUS_READY)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    points_to_pass = models.PositiveIntegerField(default=0)
    course_instance = models.ForeignKey(CourseInstance, related_name="categories")
    #hidden_to = models.ManyToManyField(UserProfile, related_name="hidden_categories",
    #    blank=True, null=True)

    class Meta:
        unique_together = ("name", "course_instance")

    def __str__(self):
        return self.name

    #def is_hidden_to(self, user_profile):
    #    return self.hidden_to.filter(id=user_profile.id).exists()

    #def set_hidden_to(self, user_profile, hide=True):
    #    if hide and not self.is_hidden_to(user_profile):
    #        self.hidden_to.add(user_profile)
    #    elif not hide and self.is_hidden_to(user_profile):
    #        self.hidden_to.remove(user_profile)
