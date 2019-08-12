import datetime
import json
import logging
import string
import urllib.request, urllib.parse
from random import randint, choice

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models
from django.db.models import Q, Count
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django_colortag.models import ColorTag

from apps.models import BaseTab, BasePlugin
from lib.email_messages import email_course_error
from lib.fields import PercentField
from lib.helpers import (
    Enum,
    get_random_string,
    resize_image,
    roman_numeral,
    safe_file_name,
    url_with_query_in_data
)
from lib.remote_page import RemotePage, RemotePageException
from lib.models import UrlMixin
from lib.validators import generate_url_key_validator
from userprofile.models import User, UserProfile, GraderUser

logger = logging.getLogger('aplus.course')

# Read pseudonymization data from file
with open(finders.find('pseudonym.json')) as json_file:
    DATA = json.load(json_file)

class Course(UrlMixin, models.Model):
    """
    Course model represents a course in a university. A course has a name and an
    identification number. It also has a URL which is included in the addresses
    of pages under the course.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    url = models.CharField(unique=True, max_length=255, blank=False,
        validators=[generate_url_key_validator()],
        help_text=_("Input an URL identifier for this course."))
    teachers = models.ManyToManyField(UserProfile,
        related_name="teaching_courses", blank=True)

    def __str__(self):
        return "{} {}".format(self.code, self.name)

    def clean(self):
        super().clean()
        RESERVED = ("admin", "accounts", "shibboleth", "api",
            "archive", "course", "exercise", "diploma")
        if self.url in RESERVED:
            raise ValidationError({
                'url':_("Taken words include: {}").format(
                    ", ".join(RESERVED))
            })

    def is_teacher(self, user):
        return (
            user and
            user.is_authenticated and (
                user.is_superuser or (
                    isinstance(user, User) and
                    self.teachers.filter(id=user.userprofile.id).exists()
                ) or (
                    isinstance(user, GraderUser) and
                    user._course == self
                )
            )
        )


    ABSOLUTE_URL_NAME = "course-instances"

    def get_url_kwargs(self):
        return dict(course_slug=self.url)


class StudentGroup(models.Model):
    """
    Stores a user group for a course instance.
    """
    course_instance = models.ForeignKey('CourseInstance', on_delete=models.CASCADE,
        related_name='groups')
    members = models.ManyToManyField(UserProfile, related_name='groups')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course_instance','timestamp']

    @classmethod
    def get_exact(cls, course_instance, member_profiles):
        for group in cls.objects.filter(
            course_instance=course_instance,
            members=member_profiles[0]
        ):
            if group.equals(member_profiles):
                return group
        return None

    @classmethod
    def filter_collaborators_of(cls, members, profile):
        return [p for p in members if p != profile]

    @classmethod
    def format_collaborator_names(cls, members, profile):
        return ", ".join(p.user.get_full_name()
            for p in cls.filter_collaborators_of(members, profile))

    def equals(self, profiles):
        return set(self.members.all()) == set(profiles)

    def collaborators_of(self, profile):
        return self.filter_collaborators_of(self.members.all(), profile)

    def collaborator_names(self, profile):
        return self.format_collaborator_names(self.members.all(), profile)


class Enrollment(models.Model):
    """
    Maps an enrolled student in a course instance.
    """
    course_instance = models.ForeignKey('CourseInstance', on_delete=models.CASCADE)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    personal_code = models.CharField(max_length=10, blank=True, default='')
    selected_group = models.ForeignKey(StudentGroup, on_delete=models.SET_NULL,
        blank=True, null=True, default=None)
    anon_name = models.CharField(max_length=50, blank=True, default='')
    anon_id = models.CharField(max_length=50, blank=True, null=True, unique=True)

def create_enrollment_code(sender, instance, created, **kwargs):
    if created:
        easychars = '0123456789ABCDEFGHJKLMNPQRSTUVXYZ'
        code = get_random_string(6, easychars)
        while Enrollment.objects.filter(course_instance=instance.course_instance, personal_code=code).exists():
            code = get_random_string(6, easychars)
        instance.personal_code = code
        instance.save()

def create_anon_id(sender, instance, created, **kwargs):
    if created or not instance.anon_id:
        nums = string.digits + string.ascii_lowercase
        code = get_random_string(16, nums)
        i = 0
        while Enrollment.objects.filter(anon_id=code).exists():
            code = get_random_string(16, nums)
            i += 1
            if i > 10000:
                raise RuntimeError("No anonymous user ids available")
        instance.anon_id = code
        instance.save(update_fields=['anon_id'])

def pseudonymize(sender, instance, created, **kwargs):
    if created or not instance.anon_name:
        def namegen():
            '''
             If the color-animal pairs are starting to run out, add another color.
             This is highly unlikely, as there are roughly 140*68=9520 possible combinations
            '''
            second_name = ""
            if Enrollment.objects.filter(course_instance=instance.course_instance).count() > len(DATA["colors"]) * len(DATA["animals"]) * 0.75:
                second_name = choice(DATA["colors"])["name"]
            return choice(DATA["colors"])["name"] + second_name + " " + choice(DATA["animals"])

        codename = namegen()
        i = 0
        while Enrollment.objects.filter(course_instance=instance.course_instance, anon_name=codename).exists():
            codename = namegen()
            i += 1
            if i > 10000:
                raise RuntimeError("No anonymous usernames available")
        instance.anon_name = codename
        instance.save(update_fields=['anon_name'])

post_save.connect(create_enrollment_code, sender=Enrollment)
post_save.connect(create_anon_id, sender=Enrollment)
post_save.connect(pseudonymize, sender=Enrollment)


class UserTag(UrlMixin, ColorTag):
    course_instance = models.ForeignKey('CourseInstance', on_delete=models.CASCADE,
        related_name="usertags")
    visible_to_students = models.BooleanField(default=False)

    class Meta:
        ordering = ['course_instance', 'name']

    def get_url_kwargs(self):
        return dict(tag_id=self.id, **self.course_instance.get_url_kwargs())

    def is_valid_slug(self, slug_candidate):
        assert self.course_instance
        return slug_candidate != '' and not UserTag.objects.filter(
            course_instance=self.course_instance,
            slug=slug_candidate,
        ).exists()


class HardcodedUserTag(UserTag):
    class Meta:
        proxy = True

    data_attrs = {
        '-removable': 'false'
    }

    def __init__(self, **kwargs):
        from django.db.models.base import DEFERRED
        kwargs.setdefault('course_instance', DEFERRED)
        kwargs.setdefault('visible_to_students', True)
        super().__init__(**kwargs)

    def save(self, *args, **kwargs):
        raise RuntimeError("Hardcoded tags can not be saved!")


USERTAG_INTERNAL = HardcodedUserTag(
    name=getattr(settings, 'INTERNAL_USER_LABEL', _('internal')),
    slug='user-internal',
    description=_("The user profile contains a student number and has logged in via local organisation authentication"),
    color='#006cb4',
)


USERTAG_EXTERNAL = HardcodedUserTag(
    name=getattr(settings, 'EXTERNAL_USER_LABEL', _('external')),
    slug='user-external',
    description=_("The user profile doesn't have a student number, thus the user has logged in from a different organization or via social authentication"),
    color='#545454',
)


class UserTaggingManager(models.Manager):

    def tags_for_instance(self, course_instance):
        ts = self.filter(course_instance=course_instance)\
            .select_related('tag')
        return [t.tag for t in ts]

    def get_all(self, profile, course_instance):
        qs = (self.filter(user=profile,
                          course_instance=course_instance)
              .select_related('tag'))
        tags = [USERTAG_EXTERNAL if profile.is_external else USERTAG_INTERNAL]
        tags.extend(t.tag for t in qs.all())
        return tags

    def set(self, profile, tag):
        return self.get_or_create(
            tag=tag,
            user=profile,
            course_instance=tag.course_instance,
        )

    def unset(self, profile, tag):
        self.filter(
            tag=tag,
            user=profile,
        ).delete()


class UserTagging(models.Model):
    tag = models.ForeignKey(UserTag,
                            on_delete=models.CASCADE,
                            related_name="taggings")
    user = models.ForeignKey(UserProfile,
                             on_delete=models.CASCADE,
                             related_name="taggings",
                             db_index=True)
    course_instance = models.ForeignKey('CourseInstance',
                                        on_delete=models.CASCADE,
                                        related_name="taggings",
                                        db_index=True)
    objects = UserTaggingManager()

    def __str__(self):
        return 'tag: {tag}, user: {user}'.format(
            tag=self.tag.name,
            user=self.user.user.username
        )

    class Meta:
        unique_together = ('tag', 'user', 'course_instance')
        index_together = (
            ('user', 'course_instance'),
        )
        ordering = ['tag']


def get_course_visibility_filter(user, prefix=None):
    class OR(Q):
        default = Q.OR

    filters = (
        ('visible_to_students', True),
    )
    if isinstance(user, User):
        user = user.userprofile
        filters += (
            ('assistants', user),
            ('course__teachers', user),
        )
    elif isinstance(user, GraderUser):
        filters += (
            ('course', user._course),
        )
    filters = dict(
        ((prefix+name if prefix else name), val)
        for name, val in filters
    )
    return OR(**filters)


class CourseInstanceManager(models.Manager):
    """
    Helpers in CourseInstance.objects
    """

    def get_queryset(self):
        return super().get_queryset().select_related('course').order_by('-starting_time')

    def get_visible(self, user=None):
        if not user or not user.is_authenticated:
            return self.filter(visible_to_students=True)
        if not user.is_superuser:
            return self.filter(get_course_visibility_filter(user)).distinct()
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
    ENROLLMENT_AUDIENCE = Enum([
        ('INTERNAL_USERS', 1, _('Internal users')),
        ('EXTERNAL_USERS', 2, _('External users')),
        ('ALL_USERS', 3, _('Internal and external users')),
    ])
    VIEW_ACCESS = Enum([
        ('ENROLLED', 1, _('Enrolled students')),
        ('ENROLLMENT_AUDIENCE', 2, _('Enrollment audience')),
        ('ALL_REGISTERED', 3, _('All registered users')),
        ('PUBLIC', 4, _('Public to internet')),
    ])
    INDEX_TYPE = Enum([
        ('RESULTS', 0, _('User results')),
        ('TOC', 1, _("Table of contents")),
        ('LAST', 2, _("Link to last visited content")),
        ('EXPERIMENT', 10, _("Experimental setup (hard-coded)")),
    ])
    CONTENT_NUMBERING = Enum([
        ('NONE', 0, _("No numbering")),
        ('ARABIC', 1, _("Arabic")),
        ('ROMAN', 2, _("Roman")),
        ('HIDDEN', 3, _("Hidden arabic")),
    ])

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="instances")
    instance_name = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=False,
        validators=[generate_url_key_validator()],
        help_text=_("Input an URL identifier for this course instance."))
    visible_to_students = models.BooleanField(default=True)
    enrollment_audience = models.IntegerField(choices=ENROLLMENT_AUDIENCE.choices,
                                              default=ENROLLMENT_AUDIENCE.INTERNAL_USERS)
    view_content_to = models.IntegerField(choices=VIEW_ACCESS.choices,
                                          default=VIEW_ACCESS.ENROLLED)
    starting_time = models.DateTimeField()
    ending_time = models.DateTimeField()
    lifesupport_time = models.DateTimeField(blank=True, null=True)
    archive_time = models.DateTimeField(blank=True, null=True)
    enrollment_starting_time = models.DateTimeField(blank=True, null=True)
    enrollment_ending_time = models.DateTimeField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True, upload_to=build_upload_dir)
    language = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True)
    footer = models.TextField(blank=True)
    index_mode = models.IntegerField(choices=INDEX_TYPE.choices, default=INDEX_TYPE.RESULTS,
        help_text=_('Select content for the course index page.'))
    module_numbering = models.IntegerField(choices=CONTENT_NUMBERING.choices,
                                           default=CONTENT_NUMBERING.ARABIC)
    content_numbering = models.IntegerField(choices=CONTENT_NUMBERING.choices,
                                            default=CONTENT_NUMBERING.ARABIC)
    head_urls = models.TextField(blank=True,
        help_text=_("External CSS and JS resources "
            "that are included on all course pages. "
            "Separate with white space."))
    configure_url = models.URLField(blank=True)
    build_log_url = models.URLField(blank=True)
    last_modified = models.DateTimeField(auto_now=True, blank=True, null=True)
    technical_error_emails = models.CharField(max_length=255, blank=True,
        help_text=_("By default exercise errors are reported to teacher "
            "email addresses. Set this field as comma separated emails to "
            "override the recipients."))
    plugins = GenericRelation(BasePlugin, object_id_field="container_pk",
                                      content_type_field="container_type")
    tabs = GenericRelation(BaseTab, object_id_field="container_pk",
                                   content_type_field="container_type")

    assistants = models.ManyToManyField(UserProfile, related_name="assisting_courses", blank=True)
    students = models.ManyToManyField(UserProfile, related_name="enrolled", blank=True, through='Enrollment')
    # usertags from course.models.UserTag
    # taggings from course.models.UserTagging
    # categories from course.models.LearningObjectCategory
    # course_modules from course.models.CourseModule

    objects = CourseInstanceManager()

    class Meta:
        unique_together = ("course", "url")

    def __str__(self):
        return "{}: {}".format(str(self.course), self.instance_name)

    def clean(self):
        super().clean()
        errors = {}
        if self.ending_time <= self.starting_time:
            errors['ending_time'] = _("Ending time must be later than starting time.")
        if self.lifesupport_time and self.lifesupport_time < self.ending_time:
            errors['lifesupport_time'] = _("Lifesupport time must be later than ending time.")
        if (self.archive_time and not self.lifesupport_time) \
                or (self.lifesupport_time and not self.archive_time):
            # Must not set only one of lifesupport and archive time since their
            # default values could change their order. Lifesupport time must not
            # be earlier than archive time.
            errors['archive_time'] = _("Lifesupport time and archive time must be either both set or both unset.")
        elif self.archive_time and self.archive_time < self.lifesupport_time:
            errors['archive_time'] = _("Archive time must be later than lifesupport time.")
        if self.language.startswith("|"):
            langs = list(filter(None, self.language.split("|"))) # remove pipes & empty strings
            for lang in langs:
                if not self.is_valid_language(lang):
                    if "language" in errors:
                        errors['language'] += (", " + lang)
                    else:
                        errors['language'] = _("Language code(s) missing from settings: ") + lang
        elif not self.is_valid_language(self.language):
            errors['language'] = _("Language code missing from settings.")
        if errors:
            raise ValidationError(errors)

    def is_valid_language(self, lang):
        return lang == "" or lang in [key for key,name in settings.LANGUAGES]

    def save(self, *args, **kwargs):
        """
        Saves the model.
        """
        super().save(*args, **kwargs)
        if self.image:
            resize_image(self.image.path, (800,600))

    def is_assistant(self, user):
        return (
            user and
            user.is_authenticated and
            isinstance(user, User) and
            self.assistants.filter(id=user.userprofile.id).exists()
        )

    def is_teacher(self, user):
        return self.course.is_teacher(user)

    def is_course_staff(self, user):
        return self.is_teacher(user) or self.is_assistant(user)

    def is_student(self, user):
        return (
            user and
            user.is_authenticated and
            isinstance(user, User) and
            self.students.filter(id=user.userprofile.id).exists()
        )

    def is_enrollable(self, user):
        if user and user.is_authenticated and self.visible_to_students:
            if self.enrollment_audience == self.ENROLLMENT_AUDIENCE.INTERNAL_USERS:
                return not user.userprofile.is_external
            if self.enrollment_audience == self.ENROLLMENT_AUDIENCE.EXTERNAL_USERS:
                return user.userprofile.is_external
            return True
        return False

    def enroll_student(self, user):
        if user and user.is_authenticated:
            Enrollment.objects.get_or_create(course_instance=self, user_profile=user.userprofile)

    def tag_user(self, user, tag):
        UserTagging.objects.create(tag=tag, user=user.userprofile, course_instance=self)

    def get_enrollment_for(self, user):
        return Enrollment.objects.filter(course_instance=self, user_profile=user.userprofile).first()

    def get_user_tags(self, user):
        return self.taggings.filter(user=user.uesrprofile).select_related('tag')

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

    def is_open(self, when=None):
        when = when or timezone.now()
        return self.starting_time <= when <= self.ending_time

    def is_past(self, when=None):
        when = when or timezone.now()
        return self.ending_time < when

    def is_on_lifesupport(self, when=None):
        when = when or timezone.now()
        return self.lifesupport_start < when

    def is_archived(self, when=None):
        when = when or timezone.now()
        return self.archive_start < when

    @property
    def archive_start(self):
        if self.archive_time: # not null
            return self.archive_time
        return self.ending_time + datetime.timedelta(days=365)

    @property
    def lifesupport_start(self):
        if self.lifesupport_time: # not null
            return self.lifesupport_time
        return self.ending_time + datetime.timedelta(days=365)

    @property
    def enrollment_start(self):
        return self.enrollment_starting_time or self.starting_time

    @property
    def enrollment_end(self):
        return self.enrollment_ending_time or self.ending_time

    def is_enrollment_open(self):
        return self.enrollment_start <= timezone.now() <= self.enrollment_end

    def has_enrollment_closed(self):
        return timezone.now() > self.enrollment_end

    def is_visible_to(self, user=None):
        if self.visible_to_students:
            return True
        return user and self.is_course_staff(user)

    @property
    def head_css_urls(self):
        return [url for url in self.head_urls.split() if ".css" in url]

    @property
    def head_js_urls(self):
        return [url for url in self.head_urls.split() if ".js" in url]

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
    course_instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE,
        related_name="course_hooks")

    def __str__(self):
        return "{} -> {}".format(self.course_instance, self.hook_url)

    def trigger(self, data):
        logger = logging.getLogger('aplus.hooks')
        try:
            urllib.request.urlopen(
                url,
                urllib.parse.urlencode(data).encode('ascii'),
                timeout=10,
            )
            logger.info("%s posted to %s on %s with %s",
                        self.hook_type, self.hook_url, self.course_instance, data)
        except:
            logger.error("HTTP POST failed on %s hook to %s (%s)",
                         self.hook_type, self.hook_url, self.course_instance)


class CourseModuleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            'course_instance', 'course_instance__course')

    def get_visible(self, user=None):
        if not user or not user.is_authenticated:
            return self.filter(
                course_instance__visible_to_students=True,
                opening_time__lte=timezone.now(),
            )
        if not user.is_superuser:
            return self.filter(
                get_course_visibility_filter(user, 'course_instance__'),
                opening_time__lte=timezone.now(),
            ).distinct()
        return self.all()


class CourseModule(UrlMixin, models.Model):
    """
    CourseModule objects connect chapters and learning objects to logical sets
    of each other and course instances. They also contain information about the
    opening times and deadlines for exercises.
    """
    STATUS = Enum([
        ('READY', 'ready', _("Ready")),
        ('UNLISTED', 'unlisted', _("Unlisted in table of contents")),
        ('HIDDEN', 'hidden', _("Hidden")),
        ('MAINTENANCE', 'maintenance', _("Maintenance")),
    ])
    status = models.CharField(max_length=32,
        choices=STATUS.choices, default=STATUS.READY)
    order = models.IntegerField(default=1)
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255,
                       validators=[generate_url_key_validator()],
                       help_text=_("Input an URL identifier for this module."))
    points_to_pass = models.PositiveIntegerField(default=0)
    introduction = models.TextField(blank=True)
    course_instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE,
        related_name="course_modules")
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
            if self.course_instance.module_numbering == CourseInstance.CONTENT_NUMBERING.ARABIC:
                return "{:d}. {}".format(self.order, self.name)
            elif self.course_instance.module_numbering == CourseInstance.CONTENT_NUMBERING.ROMAN:
                return "{} {}".format(roman_numeral(self.order), self.name)
        return self.name

    def clean(self):
        super().clean()
        errors = {}
        RESERVED = ("toc", "teachers", "user", "exercises", "apps", "lti-login")
        if self.url in RESERVED:
            errors['url'] = _("Taken words include: {}").format(", ".join(RESERVED))
        if self.opening_time > self.closing_time:
            errors['opening_time'] = _("Opening time must be earlier than the closing time.")
        if self.late_submissions_allowed and self.late_submission_deadline <= self.closing_time:
            errors['late_submission_deadline'] = _("Late submission deadline must be later than the closing time.")
        if errors:
            raise ValidationError(errors)

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

    def is_closed(self, when=None):
        when = when or timezone.now()
        if self.late_submissions_allowed and self.late_submission_penalty < 1:
            return when > self.late_submission_deadline
        return when > self.closing_time

    def are_requirements_passed(self, cached_points):
        for r in self.requirements.all():
            if not r.is_passed(cached_points):
                return False
        return True

    def get_late_submission_point_worth(self):
        """
        Returns the percentage (0-100) that late submission points are worth.
        """
        point_worth = 0
        if self.late_submissions_allowed:
            point_worth = int((1.0 - self.late_submission_penalty) * 100.0)
        return point_worth

    def number_of_submitters(self):
        return self.course_instance.students\
            .filter(submissions__exercise__course_module=self).distinct().count()

    ABSOLUTE_URL_NAME = "module"

    def get_url_kwargs(self):
        return dict(module_slug=self.url, **self.course_instance.get_url_kwargs())


class LearningObjectCategory(models.Model):
    """
    Learning objects may be grouped to different categories.
    """
    STATUS = Enum([
        ('READY', 'ready', _("Ready")),
        ('NOTOTAL', 'nototal', _("No total points")),
        ('HIDDEN', 'hidden', _("Hidden")),
    ])
    status = models.CharField(max_length=32,
        choices=STATUS.choices, default=STATUS.READY)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    points_to_pass = models.PositiveIntegerField(default=0)
    course_instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE,
        related_name="categories")
    confirm_the_level = models.BooleanField(default=False,
        help_text=_("Once exercise is graded non zero it confirms all the points on the hierarchy level. Implemented as a mandatory feedback feature."))
    accept_unofficial_submits = models.BooleanField(default=False,
        help_text=_("Grade unofficial submissions after deadlines have passed or submission limits have been exceeded. The points are stored but not included in official records."))

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
