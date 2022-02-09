import datetime
import json
import logging
import string
from typing import Any, Dict, List
import urllib.request, urllib.parse
from random import randint, choice

from aplus_auth.payload import Payload, Permission
from aplus_auth import settings as auth_settings
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models
from django.db.models import F, Q, Count
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django_colortag.models import ColorTag

from apps.models import BaseTab, BasePlugin
from authorization.models import JWTAccessible
from authorization.object_permissions import register_jwt_accessible_class
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
from lib.typing import AnyUser
from lib.validators import generate_url_key_validator
from userprofile.models import User, UserProfile, GraderUser

logger = logging.getLogger('aplus.course')

# Read pseudonymization data from file
with open(finders.find('pseudonym.json')) as json_file:
    DATA = json.load(json_file)


class CourseManager(JWTAccessible["Course"], models.Manager): ...


@register_jwt_accessible_class("course")
class Course(UrlMixin, models.Model):
    """
    Course model represents a course in a university. A course has a name and an
    identification number. It also has a URL which is included in the addresses
    of pages under the course.
    """
    name = models.CharField(
        verbose_name=_('LABEL_NAME'),
        max_length=255,
    )
    code = models.CharField(
        verbose_name=_('LABEL_CODE'),
        max_length=255,
    )
    url = models.CharField(
        verbose_name=_('LABEL_URL'),
        unique=True,
        max_length=255,
        blank=False,
        help_text=_('COURSE_URL_IDENTIFIER_HELPTEXT'),
        validators=[generate_url_key_validator()],
    )

    objects = CourseManager()

    class Meta:
        verbose_name = _('MODEL_NAME_COURSE')
        verbose_name_plural = _('MODEL_NAME_COURSE_PLURAL')

    def __str__(self):
        return "{} {}".format(self.code, self.name)

    def clean(self):
        super().clean()
        RESERVED = ("admin", "accounts", "shibboleth", "api",
            "archive", "course", "exercise", "diploma")
        if self.url in RESERVED:
            raise ValidationError({
                'url': format_lazy(
                        _('TAKEN_WORDS_INCLUDE -- {}'),
                        ", ".join(RESERVED)
                    )
            })

    ABSOLUTE_URL_NAME = "course-instances"

    def get_url_kwargs(self):
        return dict(course_slug=self.url)


class StudentGroup(models.Model):
    """
    Stores a user group for a course instance.
    """
    course_instance = models.ForeignKey('CourseInstance',
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
        related_name='groups',
    )
    members = models.ManyToManyField(UserProfile,
        verbose_name=_('LABEL_MEMBERS'),
        related_name='groups',
    )
    timestamp = models.DateTimeField(
        verbose_name=_('LABEL_TIMESTAMP'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_STUDENT_GROUP')
        verbose_name_plural = _('MODEL_NAME_STUDENT_GROUP_PLURAL')
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
    ENROLLMENT_ROLE = Enum([
        ('STUDENT', 1, _('STUDENT')),
        ('ASSISTANT', 2, _('ASSISTANT')),
        ('TEACHER', 3, _('TEACHER')),
    ])
    ENROLLMENT_STATUS = Enum([
        ('ACTIVE', 1, _('ACTIVE')),
        ('REMOVED', 2, _('REMOVED')),
        ('BANNED', 3, _('BANNED')),
    ])

    course_instance = models.ForeignKey('CourseInstance',
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
    )
    user_profile = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_USER_PROFILE'),
        on_delete=models.CASCADE,
    )
    language = models.CharField(
        verbose_name=_('LABEL_LANGUAGE'),
        max_length=5,
        blank=True,
        default="",
    )
    timestamp = models.DateTimeField(
        verbose_name=_('LABEL_TIMESTAMP'),
        auto_now_add=True,
    )
    personal_code = models.CharField(
        verbose_name=_('LABEL_PERSONAL_CODE'),
        max_length=10,
        blank=True,
        default='',
    )
    selected_group = models.ForeignKey(StudentGroup,
        verbose_name=_('LABEL_SELECTED_GROUP'),
        on_delete=models.SET_NULL,
        blank=True, null=True, default=None,
    )
    anon_name = models.CharField(
        verbose_name=_('LABEL_ANON_NAME'),
        max_length=50,
        blank=True,
        default='',
    )
    anon_id = models.CharField(
        verbose_name=_('LABEL_ANON_ID'),
        max_length=50,
        unique=True,
        blank=True,
        null=True,
    )
    role = models.IntegerField(
        verbose_name=_('LABEL_ROLE'),
        choices=ENROLLMENT_ROLE.choices,
        default=ENROLLMENT_ROLE.STUDENT,
    )
    status = models.IntegerField(
        verbose_name=_('LABEL_STATUS'),
        choices=ENROLLMENT_STATUS.choices,
        default=ENROLLMENT_STATUS.ACTIVE,
    )
    from_sis = models.BooleanField(
        verbose_name=_('LABEL_FROM_SIS'),
        default=False,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_ENROLLMENT')
        verbose_name_plural = _('MODEL_NAME_ENROLLMENT_PLURAL')
        unique_together = ("course_instance", "user_profile")

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
    course_instance = models.ForeignKey('CourseInstance',
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
        related_name="usertags",
    )
    visible_to_students = models.BooleanField(
        verbose_name=_('LABEL_VISIBLE_TO_STUDENTS'),
        default=False,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_USER_TAG')
        verbose_name_plural = _('MODEL_NAME_USER_TAG_PLURAL')
        ordering = ['course_instance', 'name']

    def get_url_kwargs(self):
        return dict(tag_id=self.id, **self.course_instance.get_url_kwargs())

    def is_valid_slug(self, slug_candidate):
        assert self.course_instance
        if not slug_candidate:
            return False
        qs = self.__class__.objects.filter(
            course_instance=self.course_instance, slug=slug_candidate)
        if self.pk is not None:
            qs = qs.exclude(pk=self.pk)
        return not qs.exists()


class HardcodedUserTag(UserTag):
    class Meta:
        verbose_name = _('MODEL_NAME_HARDCODED_USER_TAG')
        verbose_name_plural = _('MODEL_NAME_HARDCODED_USER_TAG_PLURAL')
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
    name=getattr(settings, 'INTERNAL_USER_LABEL', _('INTERNAL')),
    slug='user-internal',
    description=_('INTERNAL_USER_DESCRIPTION'),
    color='#006cb4',
)


USERTAG_EXTERNAL = HardcodedUserTag(
    name=getattr(settings, 'EXTERNAL_USER_LABEL', _('EXTERNAL')),
    slug='user-external',
    description=_('EXTERNAL_USER_DESCRIPTION'),
    color='#545454',
)


class UserTaggingManager(models.Manager):

    def tags_for_instance(self, course_instance):
        ts = self.filter(course_instance=course_instance)\
            .select_related('tag')
        return [t.tag for t in ts]

    def get_all(self, profile: UserProfile, course_instance: 'CourseInstance') -> List[UserTag]:
        # Check if taggings for the course instance were prefetched
        if hasattr(profile, 'instance_taggings'):
            taggings = profile.instance_taggings
        else:
            taggings = (
                self.filter(
                    user=profile,
                    course_instance=course_instance
                )
                .select_related('tag')
            )
        tags = [USERTAG_EXTERNAL if profile.is_external else USERTAG_INTERNAL]
        tags.extend(t.tag for t in taggings)
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
        verbose_name=_('LABEL_TAG'),
        on_delete=models.CASCADE,
        related_name="taggings",
    )
    user = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_USER'),
        on_delete=models.CASCADE,
        related_name="taggings",
        db_index=True,
    )
    course_instance = models.ForeignKey('CourseInstance',
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
        related_name="taggings",
        db_index=True,
    )
    objects = UserTaggingManager()

    def __str__(self):
        return 'tag: {tag}, user: {user}'.format(
            tag=self.tag.name,
            user=self.user.user.username
        )

    class Meta:
        verbose_name = _('MODEL_NAME_USER_TAGGING')
        verbose_name_plural = _('MODEL_NAME_USER_TAGGING_PLURAL')
        unique_together = ('tag', 'user', 'course_instance')
        index_together = (
            ('user', 'course_instance'),
        )
        ordering = ['tag']


def get_course_staff_visibility_filter(user, prefix=None):
    if prefix == None:
        prefix = ''
    filter = Q()
    if isinstance(user, User):
        user = user.userprofile
        filter = (
            (Q(**{f'{prefix}enrollment__role': Enrollment.ENROLLMENT_ROLE.TEACHER})
            | Q(**{f'{prefix}enrollment__role': Enrollment.ENROLLMENT_ROLE.ASSISTANT}))
            & Q(**{f'{prefix}enrollment__status': Enrollment.ENROLLMENT_STATUS.ACTIVE})
            & Q(**{f'{prefix}enrollment__user_profile': user})
        )
    elif isinstance(user, GraderUser):
        courses = [o for _, o in user.permissions.courses]
        instances = [o for _, o in user.permissions.instances]
        filter = Q(**{f'{prefix}course__in': courses}) | Q(**{f'{prefix}id__in': instances})

    return filter


class CourseInstanceManager(JWTAccessible["CourseInstance"], models.Manager):
    """
    Helpers in CourseInstance.objects
    """

    def get_queryset(self):
        return super().get_queryset().select_related('course').order_by('-starting_time')

    def get_visible(self, user=None):
        if not user or not user.is_authenticated:
            return self.filter(visible_to_students=True)
        if not user.is_superuser:
            return self.filter(
                get_course_staff_visibility_filter(user)
                | Q(visible_to_students=True),
            ).distinct()
        return self.all()

    def get_enrolled(self, user):
        return self.filter(
            enrollment__role=Enrollment.ENROLLMENT_ROLE.STUDENT,
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__user_profile=user)

    def get_assisting(self, user):
        return self.filter(
            enrollment__role=Enrollment.ENROLLMENT_ROLE.ASSISTANT,
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__user_profile=user)

    def get_teaching(self, user):
        return self.filter(
            enrollment__role=Enrollment.ENROLLMENT_ROLE.TEACHER,
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__user_profile=user)

    def get_active(self, user):
        return self.filter(
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__user_profile=user)

    def has_access(self, user: AnyUser, payload: Payload, permission: Permission, instance: "CourseInstance") -> bool:
        # a normal user
        if user.is_authenticated and not user.is_anonymous:
            return instance.is_teacher(user)
        # a grader user
        elif user.is_authenticated and user.is_anonymous:
            config_uid = auth_settings().get_uid_for_url(instance.configure_url)
            if config_uid is None:
                logger.warning(f"Could not find public key for configure_url {instance.configure_url}. Cannot authorize JWT instance access")
                return False
            else:
                return config_uid == user.username

        return False

    def has_create_access(self, payload: Payload, kwargs: Dict[str, Any]) -> bool:
        return False


def build_upload_dir(instance, filename):
    """
    Returns the path to a directory where the instance image should be saved.
    """
    return "public/course_instance_{:d}/{}".format(
        instance.id,
        safe_file_name(filename)
    )


@register_jwt_accessible_class("instance")
class CourseInstance(UrlMixin, models.Model):
    """
    CourseInstance class represent an instance of a course. A single course may have
    several instances either at the same time or during different years. All instances
    have the same teacher, but teaching assistants and students are connected to individual
    instances.
    """
    ENROLLMENT_AUDIENCE = Enum([
        ('INTERNAL_USERS', 1, _('INTERNAL_USERS')),
        ('EXTERNAL_USERS', 2, _('EXTERNAL_USERS')),
        ('ALL_USERS', 3, _('ALL_USERS')),
    ])
    VIEW_ACCESS = Enum([
        ('ENROLLED', 1, _('ENROLLED_STUDENTS')),
        ('ENROLLMENT_AUDIENCE', 2, _('ENROLLMENT_AUDIENCE')),
        ('ALL_REGISTERED', 3, _('ALL_REGISTERED_USERS')),
        ('PUBLIC', 4, _('PUBLIC')),
    ])
    INDEX_TYPE = Enum([
        ('RESULTS', 0, _('USER_RESULTS')),
        ('TOC', 1, _('TABLE_OF_CONTENTS')),
        ('LAST', 2, _('LAST_VISITED_LINK')),
        ('EXPERIMENT', 10, _('EXPERIMENTAL_SETUP')),
    ])
    CONTENT_NUMBERING = Enum([
        ('NONE', 0, _('NUMBERING_NONE')),
        ('ARABIC', 1, _('NUMBERING_ARABIC')),
        ('ROMAN', 2, _('NUMBERING_ROMAN')),
        ('HIDDEN', 3, _('NUMBERING_HIDDEN_ARABIC')),
    ])

    course = models.ForeignKey(Course,
        verbose_name=_('LABEL_COURSE'),
        on_delete=models.CASCADE,
        related_name="instances",
    )
    instance_name = models.CharField(
        verbose_name=_('LABEL_INSTANCE_NAME'),
        max_length=255,
    )
    url = models.CharField(
        verbose_name=_('LABEL_URL'),
        max_length=255,
        blank=False,
        help_text=_('COURSE_INSTANCE_URL_IDENTIFIER_HELPTEXT'),
        validators=[generate_url_key_validator()],
    )
    visible_to_students = models.BooleanField(
        verbose_name=_('LABEL_VISIBLE_TO_STUDENTS'),
        default=True,
    )
    enrollment_audience = models.IntegerField(
        verbose_name=_('LABEL_ENROLLMENT_AUDIENCE'),
        choices=ENROLLMENT_AUDIENCE.choices,
        default=ENROLLMENT_AUDIENCE.INTERNAL_USERS,
    )
    view_content_to = models.IntegerField(
        verbose_name=_('LABEL_VIEW_CONTENT_TO'),
        choices=VIEW_ACCESS.choices,
        default=VIEW_ACCESS.ENROLLED,
    )
    starting_time = models.DateTimeField(
        verbose_name=_('LABEL_STARTING_TIME'),
    )
    ending_time = models.DateTimeField(
        verbose_name=_('LABEL_ENDING_TIME'),
    )
    lifesupport_time = models.DateTimeField(
        verbose_name=_('LABEL_LIFESUPPORT_TIME'),
        blank=True, null=True,
    )
    archive_time = models.DateTimeField(
        verbose_name=_('LABEL_ARCHIVE_TIME'),
        blank=True, null=True,
    )
    enrollment_starting_time = models.DateTimeField(
        verbose_name=_('LABEL_ENROLLMENT_STARTING_TIME'),
        blank=True, null=True,
    )
    enrollment_ending_time = models.DateTimeField(
        verbose_name=_('LABEL_ENROLLMENT_ENDING_TIME'),
        blank=True, null=True,
    )
    image = models.ImageField(
        verbose_name=_('LABEL_IMAGE'),
        blank=True, null=True,
        upload_to=build_upload_dir,
    )
    language = models.CharField(
        verbose_name=_('LABEL_LANGUAGE'),
        max_length=255,
        blank=True,
        default="",
    )
    description = models.TextField(
        verbose_name=_('LABEL_DESCRIPTION'),
        blank=True,
    )
    footer = models.TextField(
        verbose_name=_('LABEL_FOOTER'),
        blank=True,
    )
    index_mode = models.IntegerField(
        verbose_name=_('LABEL_INDEX_MODE'),
        choices=INDEX_TYPE.choices, default=INDEX_TYPE.RESULTS,
        help_text=_('COURSE_INSTANCE_INDEX_CONTENT_SELECTION_HELPTEXT'),
    )
    module_numbering = models.IntegerField(
        verbose_name=_('LABEL_MODULE_NUMBERING'),
        choices=CONTENT_NUMBERING.choices,
        default=CONTENT_NUMBERING.ARABIC,
    )
    content_numbering = models.IntegerField(
        verbose_name=_('LABEL_CONTENT_NUMBERING'),
        choices=CONTENT_NUMBERING.choices,
        default=CONTENT_NUMBERING.ARABIC,
    )
    head_urls = models.TextField(
        verbose_name=_('LABEL_HEAD_URLS'),
        blank=True,
        help_text=_('COURSE_INSTANCE_EXTERNAL_CSS_AND_JS_FOR_ALL_PAGES_HELPTEXT'),
    )
    configure_url = models.URLField(blank=True)
    build_log_url = models.URLField(blank=True)
    last_modified = models.DateTimeField(auto_now=True, blank=True, null=True)
    technical_error_emails = models.CharField(
        verbose_name=_('LABEL_TECHNICAL_ERROR_EMAILS'),
        max_length=255,
        blank=True,
        help_text=_('COURSE_INSTANCE_EXERCISE_ERROR_EMAIL_RECIPIENT_OVERRIDE_HELPTEXT'),
    )
    plugins = GenericRelation(BasePlugin, object_id_field="container_pk",
                                      content_type_field="container_type")
    tabs = GenericRelation(BaseTab, object_id_field="container_pk",
                                   content_type_field="container_type")

    sis_id = models.CharField(
        verbose_name=_('LABEL_SIS_IDENTIFIER'),
        max_length=255,
        blank=True,
        default="",
    )

    sis_enroll = models.BooleanField(
        verbose_name=_('LABEL_SIS_ENROLL'),
        default=False,
        help_text=_('COURSE_INSTANCE_SIS_ENROLL_HELP')
    )

    # usertags from course.models.UserTag
    # taggings from course.models.UserTagging
    # categories from course.models.LearningObjectCategory
    # course_modules from course.models.CourseModule

    objects = CourseInstanceManager()

    class Meta:
        verbose_name = _('MODEL_NAME_COURSE_INSTANCE')
        verbose_name_plural = _('MODEL_NAME_COURSE_INSTANCE_PLURAL')
        unique_together = ("course", "url")

    def __str__(self):
        return "{}: {}".format(str(self.course), self.instance_name)

    def clean(self):
        super().clean()
        errors = {}
        RESERVED = ("instances",)
        if self.instance_name in RESERVED:
            errors['instance_name'] = format_lazy(_('COURSE_INSTANCE_ERROR_INSTANCE_NAME -- {}'), self.instance_name)
        if self.url in RESERVED:
            errors['url'] = format_lazy(_('COURSE_INSTANCE_ERROR_URL -- {}'), self.url)
        if self.ending_time <= self.starting_time:
            errors['ending_time'] = _('COURSE_INSTANCE_ERROR_ENDING_TIME_BEFORE_STARTING')
        if self.lifesupport_time and self.lifesupport_time < self.ending_time:
            errors['lifesupport_time'] = _('COURSE_INSTANCE_ERROR_LIFESUPPORT_TIME_BEFORE_ENDING')
        if (self.archive_time and not self.lifesupport_time) \
                or (self.lifesupport_time and not self.archive_time):
            # Must not set only one of lifesupport and archive time since their
            # default values could change their order. Lifesupport time must not
            # be earlier than archive time.
            errors['archive_time'] = _('COURSE_INSTANCE_ERROR_ARCHIVE_TIME_AND_LIFESUPPORT_ONLY_ONE_SET')
        elif self.archive_time and self.archive_time < self.lifesupport_time:
            errors['archive_time'] = _('COURSE_INSTANCE_ERROR_ARCHIVE_TIME_BEFORE_LIFESUPPORT')
        if self.language.startswith("|"):
            langs = list(filter(None, self.language.split("|"))) # remove pipes & empty strings
            for lang in langs:
                if not self.is_valid_language(lang):
                    if "language" in errors:
                        errors['language'] += (", " + lang)
                    else:
                        errors['language'] = _('COURSE_INSTANCE_ERROR_LANGUAGE(S)_MISSING_FROM_SETTINGS') + lang
        elif not self.is_valid_language(self.language):
            errors['language'] = _('COURSE_INSTANCE_ERROR_LANGUAGE_MISSING_FROM_SETTINGS')
        if errors:
            raise ValidationError(errors)

    def is_valid_language(self, lang):
        return lang == "" or lang in [key for key,name in settings.LANGUAGES]

    @property
    def languages(self):
        return self.language.strip('|').split('|')

    @property
    def default_language(self):
        language = self.language
        language_code = language.lstrip('|').split('|', 1)[0]
        if language_code:
            return language_code
        return settings.LANGUAGE_CODE.split('-', 1)[0]

    @property
    def students(self):
        return UserProfile.objects.filter(
            enrollment__role=Enrollment.ENROLLMENT_ROLE.STUDENT,
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__course_instance=self
        )

    @property
    def all_students(self):
        return UserProfile.objects.filter(
            enrollment__role=Enrollment.ENROLLMENT_ROLE.STUDENT,
            enrollment__course_instance=self
        ).annotate(enrollment_status=F('enrollment__status'))

    @property
    def assistants(self):
        return UserProfile.objects.filter(
            enrollment__role=Enrollment.ENROLLMENT_ROLE.ASSISTANT,
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__course_instance=self)

    @property
    def teachers(self):
        return UserProfile.objects.filter(
            enrollment__role=Enrollment.ENROLLMENT_ROLE.TEACHER,
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__course_instance=self)

    @property
    def course_staff(self):
        return UserProfile.objects.filter(
            Q(enrollment__role=Enrollment.ENROLLMENT_ROLE.TEACHER)
            | Q(enrollment__role=Enrollment.ENROLLMENT_ROLE.ASSISTANT),
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__course_instance=self)

    @property
    def course_staff_and_students(self):
        return UserProfile.objects.filter(
            enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
            enrollment__course_instance=self
        )

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
        return (
            user and
            user.is_authenticated and (
                user.is_superuser or (
                    isinstance(user, User) and
                    self.teachers.filter(id=user.userprofile.id).exists()
                ) or (
                    isinstance(user, GraderUser) and
                    (Permission.WRITE, self.course) in user.permissions.courses
                )
            )
        )

    def is_course_staff(self, user):
        return self.is_teacher(user) or self.is_assistant(user)

    def is_student(self, user):
        return (
            user and
            user.is_authenticated and
            isinstance(user, User) and
            self.students.filter(id=user.userprofile.id).exists()
        )

    def is_banned(self, user):
        return (
            user and
            user.is_authenticated and
            isinstance(user, User) and
            self.all_students.filter(
                enrollment__status=Enrollment.ENROLLMENT_STATUS.BANNED,
                id=user.userprofile.id,
            ).exists()
        )

    def is_enrollable(self, user):
        if self.is_course_staff(user):
            # Allow course staff to enroll even if the course instance is hidden
            # or the user does not belong to the enrollment audience.
            return True
        enrollment = self.get_enrollment_for(user)
        if enrollment and enrollment.status == Enrollment.ENROLLMENT_STATUS.BANNED:
            return False
        if user and user.is_authenticated and self.visible_to_students:
            if self.enrollment_audience == self.ENROLLMENT_AUDIENCE.INTERNAL_USERS:
                return not user.userprofile.is_external
            if self.enrollment_audience == self.ENROLLMENT_AUDIENCE.EXTERNAL_USERS:
                return user.userprofile.is_external
            return True
        return False

    def enroll_student(self, user, from_sis=False):
        # Return value False indicates whether that the user was already enrolled.
        if user and user.is_authenticated:
            try:
                enrollment = Enrollment.objects.get(
                    course_instance=self,
                    user_profile=user.userprofile,
                )
                if (
                    enrollment.role == Enrollment.ENROLLMENT_ROLE.STUDENT
                    and enrollment.status == Enrollment.ENROLLMENT_STATUS.ACTIVE
                ):
                    if not enrollment.from_sis and from_sis:
                        enrollment.from_sis = from_sis
                        enrollment.save()
                    return False
                enrollment.role = Enrollment.ENROLLMENT_ROLE.STUDENT
                enrollment.status = Enrollment.ENROLLMENT_STATUS.ACTIVE
                enrollment.from_sis = from_sis
                enrollment.save()
                return True
            except Enrollment.DoesNotExist:
                Enrollment.objects.create(
                    course_instance=self,
                    user_profile=user.userprofile,
                    role=Enrollment.ENROLLMENT_ROLE.STUDENT,
                    status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
                    from_sis=from_sis,
                )
                return True
        return False

    def enroll_from_sis(self) -> int:
        """
        Enroll students based on the participants information in Student Info System.
        If student has removed herself in SIS, she will also be marked as removed in A+.

        Returns
        -------
        Number of students enrolled based on this call. -1 if there was problem accessing SIS.
        """
        from .sis import get_sis_configuration, StudentInfoSystem
        from .cache.menu import invalidate_content

        sis: StudentInfoSystem = get_sis_configuration()
        if not sis:
            return -1

        count = 0
        try:
            participants = sis.get_participants(self.sis_id)
        except Exception as e:
            logger.exception(f"Error in getting participants from SIS.")
            return -1

        for i in participants:
            try:
                profile = UserProfile.get_by_student_id(i)
                if self.enroll_student(profile.user, from_sis=True):
                    count = count + 1

            except UserProfile.DoesNotExist:
                # This is a common scenario, if the user has enrolled in SIS, but not
                # yet logged in to A+, then the user profile does not exist yet.
                pass

        # Remove SIS-enrolled students who are not anymore in SIS participants,
        # for example, because they have first enrolled in SIS, but then
        # unenrolled themselves.
        students = self.all_students.filter(enrollment__from_sis=True)
        to_remove = students.exclude(student_id__in=participants)
        qs = Enrollment.objects.filter(user_profile__in=to_remove, course_instance=self)
        qs.update(status=Enrollment.ENROLLMENT_STATUS.REMOVED)
        for e in qs:
            invalidate_content(Enrollment, e)

        logger.info(f"{self}: enrolled {count} students from SIS")
        return count

    def set_users_with_role(self, users, role, remove_others_with_role=False):
        # This method is used for adding or replacing (depending on the last
        # parameter) users with a specific role, e.g. teachers and assistants.
        # It is recommended to use the convenience methods (starting with
        # "add"/"clear"/"set") for common use cases.
        for user in users:
            Enrollment.objects.update_or_create(
                course_instance=self,
                user_profile=user,
                defaults={
                    'role': role,
                    'status': Enrollment.ENROLLMENT_STATUS.ACTIVE,
                },
            )

        if remove_others_with_role:
            for enrollment in Enrollment.objects.filter(
                role=role,
                status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
                course_instance=self
            ):
                if enrollment.user_profile not in users:
                    enrollment.status = Enrollment.ENROLLMENT_STATUS.REMOVED
                    enrollment.save()

    def add_assistant(self, user):
        self.set_users_with_role([user], Enrollment.ENROLLMENT_ROLE.ASSISTANT)

    def clear_assistants(self):
        self.set_users_with_role([], Enrollment.ENROLLMENT_ROLE.ASSISTANT, remove_others_with_role=True)

    def set_assistants(self, users):
        self.set_users_with_role(users, Enrollment.ENROLLMENT_ROLE.ASSISTANT, remove_others_with_role=True)

    def add_teacher(self, user):
        self.set_users_with_role([user], Enrollment.ENROLLMENT_ROLE.TEACHER)

    def clear_teachers(self):
        self.set_users_with_role([], Enrollment.ENROLLMENT_ROLE.TEACHER, remove_others_with_role=True)

    def set_teachers(self, users):
        self.set_users_with_role(users, Enrollment.ENROLLMENT_ROLE.TEACHER, remove_others_with_role=True)

    def tag_user(self, user, tag):
        UserTagging.objects.create(tag=tag, user=user.userprofile, course_instance=self)

    def get_enrollment_for(self, user):
        try:
            return Enrollment.objects.get(course_instance=self, user_profile=user.userprofile)
        except Enrollment.DoesNotExist:
            return None

    def get_user_tags(self, user):
        return self.taggings.filter(user=user.uesrprofile).select_related('tag')

    def get_course_staff_profiles(self):
        return self.course_staff.all()

    def get_student_profiles(self):
        return self.students.all()

    def get_submitted_profiles(self):
        return UserProfile.objects\
            .filter(submissions__exercise__course_module__course_instance=self)\
            .distinct()\
            .exclude(
                Q(enrollment__role=Enrollment.ENROLLMENT_ROLE.TEACHER)
                | Q(enrollment__role=Enrollment.ENROLLMENT_ROLE.ASSISTANT),
                enrollment__status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
                enrollment__course_instance=self)

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

    hook_url = models.URLField(
        verbose_name=_('LABEL_HOOK_URL')
    )
    hook_type = models.CharField(
        verbose_name=_('LABEL_HOOK_TYPE'),
        max_length=12,
        choices=HOOK_CHOICES, default="post-grading",
    )
    course_instance = models.ForeignKey(CourseInstance,
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
        related_name="course_hooks",
    )

    class Meta:
        verbose_name = _('MODEL_NAME_COURSE_HOOK')
        verbose_name_plural = _('MODEL_NAME_COURSE_HOOK_PLURAL')

    def __str__(self):
        return "{} -> {}".format(self.course_instance, self.hook_url)

    def trigger(self, data):
        logger = logging.getLogger('aplus.hooks')
        url, data = url_with_query_in_data(self.hook_url, data)
        try:
            urllib.request.urlopen(
                url,
                urllib.parse.urlencode(data).encode('ascii'),
                timeout=10,
            )
            logger.info("%s posted to %s on %s with %s",
                        self.hook_type, self.hook_url, self.course_instance, data)
        except Exception as error:
            logger.error("HTTP POST failed on %s hook to %s (%s); %s: %s",
                         self.hook_type, self.hook_url, self.course_instance,
                         error.__class__.__name__, error)


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
                get_course_staff_visibility_filter(user, 'course_instance__')
                | Q(course_instance__visible_to_students=True, opening_time__lte=timezone.now()),
            ).distinct()
        return self.all()


class CourseModule(UrlMixin, models.Model):
    """
    CourseModule objects connect chapters and learning objects to logical sets
    of each other and course instances. They also contain information about the
    opening times and deadlines for exercises.
    """
    STATUS = Enum([
        ('READY', 'ready', _('STATUS_READY')),
        ('UNLISTED', 'unlisted', _('STATUS_UNLISTED')),
        ('HIDDEN', 'hidden', _('STATUS_HIDDEN')),
        ('MAINTENANCE', 'maintenance', _('STATUS_MAINTENANCE')),
    ])
    status = models.CharField(
        verbose_name=_('LABEL_STATUS'),
        max_length=32,
        choices=STATUS.choices, default=STATUS.READY,
    )
    order = models.IntegerField(
        verbose_name=_('LABEL_ORDER'),
        default=1,
    )
    name = models.CharField(
        verbose_name=_('LABEL_NAME'),
        max_length=255,
    )
    url = models.CharField(
        verbose_name=_('LABEL_URL'),
        max_length=255,
        help_text=_('MODULE_URL_IDENTIFIER_HELPTEXT'),
        validators=[generate_url_key_validator()],
    )
    points_to_pass = models.PositiveIntegerField(
        verbose_name=_('LABEL_POINTS_TO_PASS'),
        default=0)
    introduction = models.TextField(
        verbose_name=_('LABEL_INTRODUCTION'),
        blank=True,
    )
    course_instance = models.ForeignKey(CourseInstance,
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
        related_name="course_modules",
    )
    reading_opening_time = models.DateTimeField(
        verbose_name=_('LABEL_READING_OPENING_TIME'),
        blank=True, null=True,
        help_text=_('MODULE_READING_OPENING_TIME_HELPTEXT'),
    )
    opening_time = models.DateTimeField(
        verbose_name=_('LABEL_EXERCISE_OPENING_TIME'),
        default=timezone.now)
    closing_time = models.DateTimeField(
        verbose_name=_('LABEL_CLOSING_TIME'),
        default=timezone.now,
        help_text=_('MODULE_CLOSING_TIME_HELPTEXT'),
    )

    # early_submissions_allowed= models.BooleanField(default=False)
    # early_submissions_start = models.DateTimeField(default=timezone.now, blank=True, null=True)
    # early_submission_bonus  = PercentField(default=0.1,
    #   help_text=_("Multiplier of points to reward, as decimal. 0.1 = 10%"))

    late_submissions_allowed = models.BooleanField(
        verbose_name=_('LABEL_LATE_SUBMISSIONS_ALLOWED'),
        default=False,
    )
    late_submission_deadline = models.DateTimeField(
        verbose_name=_('LABEL_LATE_SUBMISSION_DEADLINE'),
        default=timezone.now,
    )
    late_submission_penalty = PercentField(
        verbose_name=_('LABEL_LATE_SUBMISSION_PENALTY'),
        default=0.5,
        help_text=_('MODULE_LATE_SUBMISSION_PENALTY_HELPTEXT'),
    )

    objects = CourseModuleManager()

    class Meta:
        verbose_name = _('MODEL_NAME_COURSE_MODULE')
        verbose_name_plural = _('MODEL_NAME_COURSE_MODULE_PLURAL')
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
            errors['url'] = format_lazy(
                _('TAKEN_WORDS_INCLUDE -- {}'),
                ", ".join(RESERVED)
            )
        if self.opening_time > self.closing_time:
            errors['opening_time'] = _('MODULE_ERROR_OPENING_TIME_AFTER_CLOSING_TIME')
        if self.late_submissions_allowed and self.late_submission_deadline <= self.closing_time:
            errors['late_submission_deadline'] = _('MODULE_ERROR_LATE_SUBMISSION_DL_BEFORE_CLOSING_TIME')
        if self.reading_opening_time and self.reading_opening_time > self.opening_time:
            errors['reading_opening_time'] = _('MODULE_ERROR_READING_OPENING_TIME_AFTER_EXERCISE_OPENING')
        if errors:
            raise ValidationError(errors)

    def is_open(self, when=None):
        when = when or timezone.now()
        if self.reading_opening_time:
            return self.reading_opening_time <= when <= self.closing_time
        return self.opening_time <= when <= self.closing_time

    def is_after_open(self, when=None):
        """
        Checks if current time is past the round opening time.
        """
        when = when or timezone.now()
        if self.reading_opening_time:
            return self.reading_opening_time <= when
        return self.opening_time <= when

    def have_exercises_been_opened(self, when=None):
        when = when or timezone.now()
        return self.opening_time <= when

    def exercises_open(self, when=None):
        when = when or timezone.now()
        return self.opening_time <= when <= self.closing_time

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
        ('READY', 'ready', _('STATUS_READY')),
        ('NOTOTAL', 'nototal', _('STATUS_NO_TOTAL_POINTS')),
        ('HIDDEN', 'hidden', _('STATUS_HIDDEN')),
    ])
    status = models.CharField(
        verbose_name=_('LABEL_STATUS'),
        max_length=32,
        choices=STATUS.choices, default=STATUS.READY,
    )
    name = models.CharField(
        verbose_name=_('LABEL_NAME'),
        max_length=255,
    )
    description = models.TextField(
        verbose_name=_('LABEL_DESCRIPTION'),
        blank=True,
    )
    points_to_pass = models.PositiveIntegerField(
        verbose_name=_('LABEL_POINTS_TO_PASS'),
        default=0,
    )
    course_instance = models.ForeignKey(CourseInstance,
        verbose_name=_('LABEL_COURSE_INSTANCE'),
        on_delete=models.CASCADE,
        related_name="categories",
    )
    confirm_the_level = models.BooleanField(
        verbose_name=_('LABEL_CONFIRM_THE_LEVEL'),
        default=False,
        help_text=_('LEARNING_OBJECT_CATEGORY_LEVEL_CONFIRMATION_EXERCISE_HELPTEXT'),
    )
    accept_unofficial_submits = models.BooleanField(
        verbose_name=_('LABEL_ACCEPT_UNOFFICIAL_SUBMITS'),
        default=False,
        help_text=_('LEARNING_OBJECT_CATEGORY_ACCEPT_UNOFFICIAL_SUBMISSIONS_HELPTEXT'),
    )

    #hidden_to = models.ManyToManyField(UserProfile, related_name="hidden_categories",
    #    blank=True, null=True)

    class Meta:
        verbose_name = _('MODEL_NAME_LEARNING_OBJECT_CATEGORY')
        verbose_name_plural = _('MODEL_NAME_LEARNING_OBJECT_CATEGORY_PLURAL')
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
