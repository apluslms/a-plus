import json
import os
from typing import Any, TYPE_CHECKING, List, Optional, Tuple
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.storage import default_storage
from django.http.request import HttpRequest
from django.db import models
from django.db.models import signals
from django.db.models.signals import post_delete, post_save
from django.template import loader
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.formats import date_format
from django.utils.text import format_lazy
from django.utils.translation import get_language, gettext_lazy as _

from aplus.api import api_reverse
from authorization.models import JWTAccessible
from authorization.object_permissions import register_jwt_accessible_class
from course.models import Enrollment, StudentGroup, CourseInstance, CourseModule, LearningObjectCategory
from external_services.lti import CustomStudentInfoLTIRequest
from external_services.models import LTIService
from inheritance.models import ModelWithInheritance, ModelWithInheritanceManager
from lib.api.authentication import (
    get_graderauth_submission_params,
    get_graderauth_exercise_params,
)
from lib.fields import DefaultForeignKey, DefaultOneToOneField, JSONField
from lib.helpers import (
    Enum,
    update_url_params,
    safe_file_name,
    roman_numeral,
    build_aplus_url,
)
from lib.models import UrlMixin
from lib.localization_syntax import pick_localized
from lib.validators import generate_url_key_validator
from userprofile.models import UserProfile

from .cache.exercise import ExerciseCache
from .protocol.aplus import load_exercise_page, load_feedback_page
from .protocol.exercise_page import ExercisePage
from .reveal_models import RevealRule

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
    from .submission_models import Submission, SubmissionDraft


class LearningObjectManager(ModelWithInheritanceManager):
    def get_queryset(self):
        return (
            super().get_queryset()
            .defer('description')
            .select_related(
                'course_module',
                'course_module__course_instance',
                'course_module__course_instance__course',
                'category',
            )
            .prefetch_related('parent')
        )

    def find_enrollment_exercise(self, course_instance, is_external):
        exercise = None
        if is_external:
            exercise = self.filter(
                course_module__course_instance=course_instance,
                status='enrollment_ext'
            ).first()
        return exercise or self.filter(
            course_module__course_instance=course_instance,
            status='enrollment'
        ).first()


class LearningObject(UrlMixin, ModelWithInheritance):
    """
    All learning objects inherit this model.
    """
    STATUS = Enum([
        ('READY', 'ready', _('STATUS_READY')),
        ('UNLISTED', 'unlisted', _('STATUS_UNLISTED')),
        ('ENROLLMENT', 'enrollment', _('ENROLLMENT_QUESTIONS')),
        ('ENROLLMENT_EXTERNAL', 'enrollment_ext', _('ENROLLMENT_QUESTIONS_FOR_EXTERNAL')),
        ('HIDDEN', 'hidden', _('HIDDEN_FROM_NOT_COURSE_STAFF')),
        ('MAINTENANCE', 'maintenance', _('STATUS_MAINTENANCE')),
    ])
    AUDIENCE = Enum([
        ('COURSE_AUDIENCE', 0, _('AUDIENCE_COURSE_AUDIENCE')),
        ('INTERNAL_USERS', 1, _('AUDIENCE_INTERNAL_USERS')),
        ('EXTERNAL_USERS', 2, _('AUDIENCE_EXTERNAL_USERS')),
        ('REGISTERED_USERS', 3, _('AUDIENCE_REGISTERED_USERS')),
    ])
    status = models.CharField(
        verbose_name=_('LABEL_STATUS'),
        max_length=32,
        choices=STATUS.choices, default=STATUS.READY,
    )
    audience = models.IntegerField(
        verbose_name=_('LABEL_AUDIENCE'),
        choices=AUDIENCE.choices,
        default=AUDIENCE.COURSE_AUDIENCE,
    )
    category = models.ForeignKey(LearningObjectCategory,
        verbose_name=_('LABEL_CATEGORY'),
        on_delete=models.CASCADE,
        related_name="learning_objects",
    )
    course_module = models.ForeignKey(CourseModule,
        verbose_name=_('LABEL_COURSE_MODULE'),
        on_delete=models.CASCADE,
        related_name="learning_objects",
    )
    parent = DefaultForeignKey('self',
        verbose_name=_('LABEL_PARENT'),
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='children',
    )
    order = models.IntegerField(
        verbose_name=_('LABEL_ORDER'),
        default=1,
    )
    url = models.CharField(
        verbose_name=_('LABEL_URL'),
        max_length=512,
        help_text=_('LEARNING_OBJECT_URL_IDENTIFIER_HELPTEXT'),
        validators=[generate_url_key_validator()],
    )
    name = models.CharField(
        verbose_name=_('LABEL_NAME'),
        max_length=255,
    )
    description = models.TextField(
        verbose_name=_('LABEL_DESCRIPTION'),
        blank=True,
        help_text=_('LEARNING_OBJECT_DESCRIPTION_HELPTEXT'),
    )
    use_wide_column = models.BooleanField(
        verbose_name=_('LABEL_USE_WIDE_COLUMN'),
        default=False,
        help_text=_('LEARNING_OBJECT_WIDE_COLUMN_HELPTEXT'),
    )

    service_url = models.CharField(
        verbose_name=_('LABEL_SERVICE_URL'),
        max_length=4096,
        blank=True,
    )
    exercise_info = JSONField(
        verbose_name=_('LABEL_EXERCISE_INFO'),
        blank=True,
    )
    model_answers = models.TextField(
        verbose_name=_('LABEL_MODEL_ANSWERS'),
        blank=True,
        help_text=_('LEARNING_OBJECT_MODEL_ANSWER_URLS_HELPTEXT'),
    )
    templates = models.TextField(
        verbose_name=_('LABEL_TEMPLATES'),
        blank=True,
        help_text=_('LEARNING_OBJECT_TEMPLATE_URLS_HELPTEXT'),
    )

    # Keep this to support ExerciseWithAttachment
    # Maybe this should inject extra content to any exercise
    content = models.TextField(
        verbose_name=_('LABEL_CONTENT'),
        blank=True,
    )

    objects = LearningObjectManager()

    class Meta:
        verbose_name = _('MODEL_NAME_LEARNING_OBJECT')
        verbose_name_plural = _('MODEL_NAME_LEARNING_OBJECT_PLURAL')
        app_label = "exercise"
        ordering = ['course_module', 'order', 'id']
        unique_together = ['course_module', 'parent', 'url']

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        super().clean()
        errors = {}
        RESERVED = ("submissions", "plain", "info")
        if self.url in RESERVED:
            errors['url'] = format_lazy(
                _('TAKEN_WORDS_INCLUDE -- {}'),
                ", ".join(RESERVED)
            )
        if self.course_module.course_instance != self.category.course_instance:
            errors['category'] = _('LEARNING_OBJECT_ERROR_MODULE_AND_CATEGORY_MUST_HAVE_SAME_COURSE_INSTANCE')
        if self.parent:
            if self.parent.course_module != self.course_module:
                errors['parent'] = _('LEARNING_OBJECT_ERROR_PARENT_MUST_BE_FROM_SAME_MODULE')
            if self.parent.id == self.id:
                errors['parent'] = _('LEARNING_OBJECT_ERROR_PARENT_CANNOT_BE_SELF')
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Trigger LearningObject post save signal for extending classes.
        cls = self.__class__
        while cls.__bases__:
            cls = cls.__bases__[0]
            if cls.__name__ == 'LearningObject':
                signals.post_save.send(sender=cls, instance=self)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Trigger LearningObject post delete signal for extending classes.
        cls = self.__class__
        while cls.__bases__:
            cls = cls.__bases__[0]
            if cls.__name__ == 'LearningObject':
                signals.post_delete.send(sender=cls, instance=self)

    def _build_full_name(self, force_content_numbering=None, force_module_numbering=None):
        content_numbering = (
            self.course_instance.content_numbering
            if force_content_numbering is None
            else force_content_numbering
        )
        module_numbering = (
            self.course_instance.module_numbering
            if force_module_numbering is None
            else force_module_numbering
        )
        if self.order >= 0:
            if content_numbering == CourseInstance.CONTENT_NUMBERING.ARABIC:
                number = self.number()
                if module_numbering in (
                        CourseInstance.CONTENT_NUMBERING.ARABIC,
                        CourseInstance.CONTENT_NUMBERING.HIDDEN,
                    ):
                    return "{:d}.{} {}".format(self.course_module.order, number, self.name)
                return "{} {}".format(number, self.name)
            if content_numbering == CourseInstance.CONTENT_NUMBERING.ROMAN:
                return "{} {}".format(roman_numeral(self.order), self.name)
        return self.name

    def __str__(self):
        return self._build_full_name()

    def hierarchical_name(self):
        return self._build_full_name(
            CourseInstance.CONTENT_NUMBERING.ARABIC,
            CourseInstance.CONTENT_NUMBERING.ARABIC
        )

    def number(self):
        return ".".join([str(o.order) for o in self.parent_list()])

    def parent_list(self):
        if not hasattr(self, '_parents'):
            def recursion(obj, parents):
                if obj is not None:
                    return recursion(obj.parent, [obj] + parents)
                return parents
            self._parents = recursion(self.parent, [self])
        return self._parents

    @property
    def course_instance(self):
        return self.course_module.course_instance

    @property
    def is_submittable(self):
        return False

    def is_empty(self):
        return not self.service_url and self.as_leaf_class()._is_empty()

    def _is_empty(self):
        return True

    def is_open(self, when=None):
        return self.course_module.exercises_open(when=when)

    def is_closed(self, when=None):
        return self.course_module.is_closed(when=when)

    def get_path(self):
        return "/".join([o.url for o in self.parent_list()])

    ABSOLUTE_URL_NAME = "exercise"

    def get_url_kwargs(self):
        return dict(exercise_path=self.get_path(), **self.course_module.get_url_kwargs())

    def get_display_url(self):
        if self.status == self.STATUS.UNLISTED and self.parent:
            return "{}#chapter-exercise-{:d}".format(
                self.parent_list()[-2].get_absolute_url(),
                self.order
            )
        return self.get_absolute_url()

    def get_submission_list_url(self):
        return self.get_url("submission-list")

    def load(
            self,
            request: HttpRequest,
            students: List[UserProfile],
            url_name: str = "exercise",
            ordinal: Optional[int] = None,
            ) -> ExercisePage:
        """
        Loads the learning object page.

        Provide the `ordinal` parameter ONLY when viewing previous submissions.
        In randomized exercises, it causes a specific submission's form to be
        returned.
        """
        page = ExercisePage(self)
        if not self.service_url:
            return page
        language = get_language()
        cache = ExerciseCache(self, language, request, students, url_name, ordinal)
        page.head = cache.head()
        page.content = cache.content()
        page.is_loaded = True
        return page

    def load_page( # pylint: disable=too-many-arguments
            self,
            language: str,
            request: HttpRequest,
            students: List[UserProfile],
            url_name: str,
            ordinal: Optional[int] = None,
            last_modified: Optional[str] = None,
            ) -> ExercisePage:
        return load_exercise_page(
            request,
            self.get_load_url(language, request, students, url_name, ordinal),
            last_modified,
            self
        )

    def get_service_url(self, language):
        return pick_localized(self.service_url, language)

    def get_load_url( # pylint: disable=too-many-arguments
            self,
            language: str,
            request: HttpRequest,
            students: List[UserProfile], # pylint: disable=unused-argument
            url_name: str = "exercise", # pylint: disable=unused-argument
            ordinal: Optional[int] = None, # pylint: disable=unused-argument
            ) -> str:
        return update_url_params(self.get_service_url(language), {
            'lang': language,
        })

    def get_models(self):
        entries = pick_localized(self.model_answers, get_language())
        return [(url,url.split('/')[-1].split('?', 1)[0]) for url in entries.split()]

    def get_templates(self):
        entries = pick_localized(self.templates, get_language())
        return [(url,url.split('/')[-1].split('?', 1)[0]) for url in entries.split()]

    def get_form_spec_keys(self, include_static_fields=False):
        """Return the keys of the form fields of this exercise.
        This is based on the form_spec structure of the exercise_info, which
        is saved in the course JSON import.
        """
        form_spec = (
            self.exercise_info.get('form_spec', [])
            if isinstance(self.exercise_info, dict)
            else []
        )
        keys = set()
        for item in form_spec:
            key = item.get('key')
            typ = item.get('type')
            if not include_static_fields and typ == 'static':
                continue
            if key: # avoid empty or missing values
                keys.add(key)
        return keys


def invalidate_exercise(sender, instance, **kwargs): # pylint: disable=unused-argument
    for language,_ in settings.LANGUAGES: # noqa: F402
        ExerciseCache.invalidate(instance, modifiers=[language])


# Automatically invalidate cached exercise html when edited.
post_save.connect(invalidate_exercise, sender=LearningObject)
post_delete.connect(invalidate_exercise, sender=LearningObject)


class LearningObjectDisplay(models.Model):
    """
    Records views of learning objects.
    """
    learning_object = DefaultForeignKey(LearningObject,
        verbose_name=_('LABEL_LEARNING_OBJECT'),
        on_delete=models.CASCADE,
    )
    profile = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_PROFILE'),
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField(
        verbose_name=_('LABEL_TIMESTAMP'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_LEARNING_OBJECT_DISPLAY')
        verbose_name_plural = _('MODEL_NAME_LEARNING_OBJECT_DISPLAY_PLURAL')


class CourseChapter(LearningObject):
    """
    Chapters can offer and organize learning material as one page chapters.
    """
    generate_table_of_contents = models.BooleanField(
        verbose_name=_('LABEL_GENERATE_TOC'),
        default=False,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_COURSE_CHAPTER')
        verbose_name_plural = _('MODEL_NAME_COURSE_CHAPTER_PLURAL')

    def _is_empty(self):
        return not self.generate_table_of_contents


class BaseExerciseManager(JWTAccessible["BaseExercise"], LearningObjectManager):
    pass


@register_jwt_accessible_class("exercise")
class BaseExercise(LearningObject):
    """
    The common parts for all exercises.
    """
    # Timing enumeration is only used as a return value.
    TIMING = Enum([
        ('CLOSED_BEFORE', 0, "Submissions are not yet accepted"),
        ('OPEN', 1, "Normal submissions are accepted"),
        ('LATE', 2, "Late submissions are accepted"),
        ('UNOFFICIAL', 3, "Only unofficial submissions are accepted"),
        ('CLOSED_AFTER', 4, "Submissions are not anymore accepted"),
        ('ARCHIVED', 5, "Course is archived and so are exercises"),
    ])

    SUBMIT_STATUS = Enum([
        ('ALLOWED', 1, ''),
        ('CANNOT_ENROLL', 2, 'You cannot enroll in the course.'),
        ('NOT_ENROLLED', 3, 'You must enroll at course home.'),
        ('INVALID_GROUP', 4, 'The selected group is not acceptable.'),
        ('AMOUNT_EXCEEDED', 5, 'You have used the allowed amount of submissions.'),
        ('INVALID', 999, 'You cannot submit for an unspecified reason.'),
    ])

    GRADING_MODE = Enum([
        ('BEST', 1, _('GRADING_MODE_BEST')),
        ('LAST', 2, _('GRADING_MODE_LAST')),
    ])

    allow_assistant_viewing = models.BooleanField(
        verbose_name=_('LABEL_ALLOW_ASSISTANT_VIEWING'),
        default=True,
    )
    allow_assistant_grading = models.BooleanField(
        verbose_name=_('LABEL_ALLOW_ASSISTANT_GRADING'),
        default=False,
    )
    min_group_size = models.PositiveIntegerField(
        verbose_name=_('LABEL_MIN_GROUP_SIZE'),
        default=1,
    )
    max_group_size = models.PositiveIntegerField(
        verbose_name=_('LABEL_MAX_GROUP_SIZE'),
        default=1,
    )
    max_submissions = models.PositiveIntegerField(
        verbose_name=_('LABEL_MAX_SUBMISSIONS'),
        default=10,
    )
    max_points = models.PositiveIntegerField(
        verbose_name=_('LABEL_MAX_POINTS'),
        default=100,
    )
    points_to_pass = models.PositiveIntegerField(
        verbose_name=_('LABEL_POINTS_TO_PASS'),
        default=40,
    )
    difficulty = models.CharField(
        verbose_name=_('LABEL_DIFFICULTY'),
        max_length=32,
        blank=True,
    )
    submission_feedback_reveal_rule = DefaultOneToOneField(RevealRule,
        verbose_name=_('LABEL_SUBMISSION_FEEDBACK_REVEAL_RULE'),
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
    )
    model_solutions_reveal_rule = DefaultOneToOneField(RevealRule,
        verbose_name=_('LABEL_MODEL_SOLUTIONS_REVEAL_RULE'),
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
    )
    grading_mode = models.IntegerField(
        verbose_name=_('LABEL_GRADING_MODE'),
        choices=GRADING_MODE.choices,
        default=GRADING_MODE.BEST,
        help_text=_('BASE_EXERCISE_GRADING_MODE_HELPTEXT'),
    )

    objects = BaseExerciseManager()

    if TYPE_CHECKING:
        id: models.AutoField
        deadlineruledeviation_set: RelatedManager['DeadlineRuleDeviation'] # pylint: disable=used-before-assignment
        maxsubmissionsruledeviation_set: RelatedManager['MaxSubmissionsRuleDeviation']
        submissions: RelatedManager['Submission']
        submission_drafts: RelatedManager['SubmissionDraft']

    class Meta:
        verbose_name = _('MODEL_NAME_BASE_EXERCISE')
        verbose_name_plural = _('MODEL_NAME_BASE_EXERCISE_PLURAL')
        app_label = 'exercise'

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        super().clean()
        errors = {}
        if self.points_to_pass > self.max_points:
            errors['points_to_pass'] = _('EXERCISE_ERROR_POINTS_TO_PASS_GREATER_MAX_POINTS')
        if self.min_group_size > self.max_group_size:
            errors['min_group_size'] = _('EXERCISE_ERROR_MIN_GROUP_SIZE_GREATER_MAX_SIZE')
        if errors:
            raise ValidationError(errors)

    @property
    def is_submittable(self):
        return True

    @property
    def default_submission_feedback_reveal_rule(self) -> RevealRule:
        """
        The reveal rule to be used when `submission_feedback_reveal_rule` has
        not been assigned a value.
        """
        return RevealRule(
            trigger=RevealRule.TRIGGER.IMMEDIATE,
        )

    @property
    def active_submission_feedback_reveal_rule(self) -> RevealRule:
        """
        The reveal rule that should be used for determining submission feedback
        visibility. Returns `submission_feedback_reveal_rule`, or
        `default_submission_feedback_reveal_rule` if the former has not been
        assigned a value.
        """
        return (
            self.submission_feedback_reveal_rule
            or self.default_submission_feedback_reveal_rule
        )

    @property
    def default_model_solutions_reveal_rule(self) -> RevealRule:
        """
        The reveal rule to be used when `model_solutions_reveal_rule` has
        not been assigned a value.
        """
        return RevealRule(
            trigger=RevealRule.TRIGGER.DEADLINE,
        )

    @property
    def active_model_solutions_reveal_rule(self) -> RevealRule:
        """
        The reveal rule that should be used for determining model solution
        visibility. Returns `model_solutions_reveal_rule`, or
        `default_model_solutions_reveal_rule` if the former has not been
        assigned a value.
        """
        return (
            self.model_solutions_reveal_rule
            or self.default_model_solutions_reveal_rule
        )

    def get_timing(self, students, when):
        module = self.course_module
        # Check the course instance archive time first so that submissions
        # are never accepted after it.
        dl = module.course_instance.archive_start
        if module.course_instance.is_archived(when=when):
            return self.TIMING.ARCHIVED, dl

        if not module.have_exercises_been_opened(when=when):
            return self.TIMING.CLOSED_BEFORE, module.opening_time

        category = self.category
        if module.exercises_open(when=when) or category.confirm_the_level:
            return self.TIMING.OPEN, module.closing_time

        deviation = self.one_has_deadline_deviation(students)
        dl = deviation.get_new_deadline() if deviation else None
        if dl and when <= dl:
            if deviation.without_late_penalty:
                return self.TIMING.OPEN, dl
            return self.TIMING.LATE, dl

        if module.is_late_submission_open(when=when):
            return self.TIMING.LATE, module.late_submission_deadline

        dl = dl or (module.late_submission_deadline
            if module.late_submissions_allowed else module.closing_time)
        if category.accept_unofficial_submits:
            return self.TIMING.UNOFFICIAL, dl

        return self.TIMING.CLOSED_AFTER, dl

    def delta_in_minutes_from_closing_to_date(self, future_date):
        module_close = self.course_module.closing_time
        # module_close is in utc format 2018-04-10 23:59:00+00:00
        # while future_date from the teacher submitted form might
        # be in different formet, eg. 2018-05-15 23:59:00+03:00
        # -> convert future_date to same format as module_close
        string_date = str(future_date)[:16]
        converted = timezone.make_aware(
                parse_datetime(string_date),
                timezone.get_current_timezone())
        delta = converted - module_close
        return delta.days * 24 * 60 + delta.seconds // 60

    def one_has_access(self, students, when=None):
        """
        Checks if any of the users can submit taking the granted extra time
        in consideration.
        """
        timing,d = self.get_timing(students, when or timezone.now())

        formatted_time = date_format(timezone.localtime(d), "DATETIME_FORMAT")
        if timing == self.TIMING.OPEN:
            return True,[]
        if timing == self.TIMING.LATE:
            return True,[
                format_lazy(
                    # xgettext:no-python-format
                    _('EXERCISE_TIMING_LATE -- {date}, {percent:d}'),
                    date=formatted_time,
                    percent=self.course_module.get_late_submission_point_worth(),
                )
            ]
        if timing == self.TIMING.UNOFFICIAL:
            return True,[
                format_lazy(
                    _('EXERCISE_TIMING_UNOFFICIAL -- {date}'),
                    date=formatted_time,
                )
            ]
        if timing == self.TIMING.CLOSED_BEFORE:
            return False,[
                format_lazy(
                    _('EXERCISE_TIMING_CLOSED_BEFORE -- {date}'),
                    date=formatted_time,
                )
            ]
        if timing == self.TIMING.CLOSED_AFTER:
            return False,[
                format_lazy(
                    _('EXERCISE_TIMING_CLOSED_AFTER -- {date}'),
                    date=formatted_time,
                )
            ]
        if timing == self.TIMING.ARCHIVED:
            return False,[
                format_lazy(
                    _('EXERCISE_TIMING_ARCHIVED -- {date}'),
                    date=formatted_time,
                )
            ]
        return False,["ERROR"]

    def one_has_deadline_deviation(self, students):
        deviation = None
        for profile in students:
            for d in self.deadlineruledeviation_set.filter(submitter=profile):
                if not deviation\
                        or d.get_new_deadline() > deviation.get_new_deadline():
                    deviation = d
        return deviation

    def number_of_submitters(self):
        return self.course_instance.students\
            .filter(submissions__exercise=self).distinct().count()

    def get_submissions_for_student(self, user_profile, exclude_errors=False):
        if exclude_errors:
            submissions = user_profile.submissions.exclude_errors()
        else:
            submissions = user_profile.submissions
        return submissions.filter(exercise=self)

    def max_submissions_for_student(self, user_profile):
        """
        Calculates student specific max_submissions considering the possible
        MaxSubmissionsRuleDeviation for this student.
        """
        deviation = self.maxsubmissionsruledeviation_set \
            .filter(submitter=user_profile).first()
        if deviation:
            return self.max_submissions + deviation.extra_submissions
        return self.max_submissions

    def one_has_submissions(self, students: List[UserProfile]) -> Tuple[bool, List[str]]:
        if len(students) == 1 and self.status in (self.STATUS.ENROLLMENT, self.STATUS.ENROLLMENT_EXTERNAL):
            enrollment = self.course_instance.get_enrollment_for(students[0].user)
            if not enrollment or enrollment.status != Enrollment.ENROLLMENT_STATUS.ACTIVE:
                return True, []
        submission_count = 0
        for profile in students:
            # The students are in the same group, therefore, each student should
            # have the same submission count. However, max submission deviation
            # may be set for only one group member.
            submission_count = self.get_submissions_for_student(profile, True).count()
            if submission_count < self.max_submissions_for_student(profile):
                return True, []
        # Even in situations where the student could otherwise make an infinite
        # number of submissions, there is still a hard limit.
        max_unofficial_submissions = settings.MAX_UNOFFICIAL_SUBMISSIONS
        if max_unofficial_submissions == 0 or submission_count < max_unofficial_submissions:
            if self.max_submissions == 0:
                # If max_submissions is 0, the submission limit is "infinite".
                return True, []
            if self.category.accept_unofficial_submits:
                # Note: time is not checked here, but unofficial submissions are
                # not allowed if the course archive time has passed.
                # The caller must check the time limits too.
                return True, [_('EXERCISE_MAX_SUBMISSIONS_USED_UNOFFICIAL_ALLOWED')]
        return False, [_('EXERCISE_MAX_SUBMISSIONS_USED')]

    def no_submissions_left(self, students):
        if len(students) == 1 and self.status in (self.STATUS.ENROLLMENT, self.STATUS.ENROLLMENT_EXTERNAL):
            enrollment = self.course_instance.get_enrollment_for(students[0].user)
            if not enrollment or enrollment.status != Enrollment.ENROLLMENT_STATUS.ACTIVE:
                return False
        if self.max_submissions == 0:
            return False
        for profile in students:
            if self.get_submissions_for_student(profile, True).count() \
                    <= self.max_submissions_for_student(profile):
                return False
        return True

    def check_submission_allowed(self, profile, request=None):
        """
        Checks whether the submission to this exercise is allowed for the given
        user and generates a list of warnings.

        @return: (success_flag, warning_message_list)
        """
        success, warnings, students = self._check_submission_allowed(profile, request)
        return success, list(str(w) for w in warnings), students

    def _check_submission_allowed(self, profile, request=None): # noqa: MC0001
        students = [profile]
        warnings = []

        # Let course module settings decide submissionable state.
        #if self.course_instance.ending_time < timezone.now():
        #    warnings.append(_('The course is archived. Exercises are offline.'))
        #    return False, warnings, students

        # Check enrollment requirements.
        enrollment = self.course_instance.get_enrollment_for(profile.user)
        if self.status in (
            LearningObject.STATUS.ENROLLMENT,
            LearningObject.STATUS.ENROLLMENT_EXTERNAL,
        ):
            if not self.course_instance.is_enrollment_open():
                return (self.SUBMIT_STATUS.CANNOT_ENROLL,
                        [_('ENROLLMENT_ERROR_ENROLLMENT_NOT_OPEN')],
                        students)
            if not self.course_instance.is_enrollable(profile.user):
                return (self.SUBMIT_STATUS.CANNOT_ENROLL,
                        [_('CANNOT_ENROLL_IN_COURSE')],
                        students)
        elif not enrollment or enrollment.status != Enrollment.ENROLLMENT_STATUS.ACTIVE:
            if self.course_instance.is_course_staff(profile.user):
                return (self.SUBMIT_STATUS.ALLOWED,
                        [_('STAFF_CAN_SUBMIT_WITHOUT_ENROLLING')],
                        students)
            return (self.SUBMIT_STATUS.NOT_ENROLLED,
                    [_('MUST_ENROLL_TO_SUBMIT_EXERCISES')],
                    students)

        # Support group id from post or currently selected group.
        group = None
        group_id = None
        if request:
            try:
                group_id = json.loads(request.POST.get('__aplus__', '{}')).get('group')
            except json.JSONDecodeError:
                warnings.append(_('EXERCISE_WARNING_CANNOT_SUBMIT_INVALID_JSON_IN_POST'))
                return self.SUBMIT_STATUS.INVALID, warnings, students
            if group_id is None:
                group_id = request.POST.get("_aplus_group")

        if group_id is not None:
            try:
                gid = int(group_id)
                if gid > 0:
                    group = profile.groups.filter(
                        course_instance=self.course_instance,
                        id=gid).first()
                    if group is None:
                        warnings.append(_('EXERCISE_WARNING_NO_GROUP_WITH_ID'))
                        return self.SUBMIT_STATUS.INVALID_GROUP, warnings, students
            except ValueError:
                pass
        elif enrollment and enrollment.status == Enrollment.ENROLLMENT_STATUS.ACTIVE and enrollment.selected_group:
            group = enrollment.selected_group

        if self.max_group_size > 1:
            # Check groups cannot be changed after submitting.
            submission = self.get_submissions_for_student(profile).first()
            if submission:
                if self._detect_group_changes(profile, group, submission):
                    msg = _('EXERCISE_WARNING_GROUP_CANNOT_CHANGE_FOR_SAME_EXERCISE_MSG')
                    warning = _('EXERCISE_WARNING_HAS_PREVIOUSLY_SUBMITTED_EXERCISE -- {with_group}, {msg}')
                    if submission.submitters.count() == 1:
                        warning = format_lazy(warning, with_group=_('ALONE'), msg=msg)
                    else:
                        collaborators = StudentGroup.format_collaborator_names(
                                submission.submitters.all(), profile)
                        with_group = format_lazy(_('WITH -- {}'), collaborators)
                        warning = format_lazy(warning, with_group=with_group, msg=msg)
                    warnings.append(warning)
                    return self.SUBMIT_STATUS.INVALID_GROUP, warnings, students

            elif self._detect_submissions(profile, group):
                warnings.append(
                    format_lazy(
                        _('EXERCISE_WARNING_COLLABS_HAVE_SUBMITTED_EXERCISE_WITH_DIFF_GROUP -- {collaborators}'),
                        collaborators=group.collaborator_names(profile),
                    )
                )
                return self.SUBMIT_STATUS.INVALID_GROUP, warnings, students

        # Get submitters.
        if group:
            students = list(group.members.all())

        # Check group size.
        if not (self.min_group_size <= len(students) <= self.max_group_size):
            if self.max_group_size == self.min_group_size:
                size = "{:d}".format(self.min_group_size)
            else:
                size = "{:d}-{:d}".format(self.min_group_size, self.max_group_size)
            warnings.append(
                format_lazy(
                    _('EXERCISE_WARNING_REQUIRES_GROUP_SIZE -- {size}'),
                    size=size
                )
            )
        if self.status in (self.STATUS.ENROLLMENT, self.STATUS.ENROLLMENT_EXTERNAL):
            access_ok, access_warnings = True, []
        else:
            access_ok, access_warnings = self.one_has_access(students)
        is_staff = all(self.course_instance.is_course_staff(p.user) for p in students)
        ok = (access_ok and len(warnings) == 0) or is_staff # pylint: disable=consider-using-ternary
        all_warnings = warnings + access_warnings
        if not ok:
            if len(all_warnings) == 0:
                all_warnings.append(_(
                    'EXERCISE_WARNING_CANNOT_SUBMIT_UNKNOWN_REASON'))
            return self.SUBMIT_STATUS.INVALID, all_warnings, students

        submit_limit_ok, submit_limit_warnings = self.one_has_submissions(students)
        if not submit_limit_ok and not is_staff:
            # access_warnings are not needed here
            return (self.SUBMIT_STATUS.AMOUNT_EXCEEDED,
                    submit_limit_warnings,
                    students)

        return self.SUBMIT_STATUS.ALLOWED, all_warnings + submit_limit_warnings, students

    def _detect_group_changes(self, profile, group, submission):
        submitters = list(submission.submitters.all())
        if group:
            return not group.equals(submitters)
        return len(submitters) > 1 or submitters[0] != profile

    def _detect_submissions(self, profile, group):
        if group:
            return not all((
                len(self.get_submissions_for_student(p)) == 0
                for p in group.members.all() if p != profile
            ))
        return False

    def get_total_submitter_count(self):
        return UserProfile.objects \
            .filter(submissions__exercise=self) \
            .distinct().count()

    def get_load_url( # pylint: disable=too-many-arguments
            self,
            language: str,
            request: HttpRequest,
            students: List[UserProfile],
            url_name: str = "exercise",
            ordinal: Optional[int] = None,
            ) -> str:
        if self.id:
            if request.user.is_authenticated:
                user = request.user
                if ordinal is None:
                    submission_count = self.get_submissions_for_student(
                        user.userprofile, exclude_errors=True
                    ).count()
                    ordinal = submission_count + 1
            else:
                user = None
                ordinal = 1
            # Make grader async URL for the currently authenticated user.
            # The async handler will handle group selection at submission time.
            submission_url = update_url_params(
                api_reverse("exercise-grader", kwargs={
                    'exercise_id': self.id
                }),
                get_graderauth_exercise_params(self, user),
            )
            return self._build_service_url(
                language, students,
                ordinal, url_name, submission_url
            )
        return super().get_load_url(language, request, students, url_name, ordinal)

    def grade(self, submission, request=None, no_penalties=False, url_name="exercise"):
        """
        Loads the exercise feedback page.
        """
        # Get the language from the submission
        language = submission.lang or self.course_module.course_instance.default_language

        submission_url = update_url_params(
            api_reverse("submission-grader", kwargs={
                'submission_id': submission.id
            }),
            get_graderauth_submission_params(submission),
        )
        url = self._build_service_url(
            language, submission.submitters.all(),
            submission.ordinal_number(), url_name, submission_url
        )
        try:
            return load_feedback_page(
                request, url, self, submission, no_penalties=no_penalties
            )
        except OSError as error:
            page = ExercisePage(self)
            msg = "Unable to grade the submission. %s: %s" % (
                error.__class__.__name__, error)
            page.errors.append(msg)
            return page

    def modify_post_parameters(self, data, files, user, students, request, url): # pylint: disable=too-many-arguments
        """
        Allows to modify submission POST parameters before they are sent to
        the grader. Extending classes may implement this function.
        """

    # pylint: disable-next=too-many-arguments
    def _build_service_url(self, language, students, ordinal_number, url_name, submission_url):
        """
        Generates complete URL with added parameters to the exercise service.
        """
        uid_str = '-'.join(sorted(str(profile.user.id) for profile in students)) if students else ''
        return update_url_params(self.get_service_url(language), {
            "max_points": self.max_points,
            "max_submissions": self.max_submissions,
            "submission_url": build_aplus_url(submission_url),
            "post_url": build_aplus_url(str(self.get_url(url_name)), user_url=True),
            "uid": uid_str,
            "ordinal_number": ordinal_number,
            "lang": language,
        })

    @property
    def can_regrade(self):
        """Can this exercise be regraded in the assessment service, i.e.,
        can previous submissions be uploaded again for grading?"""
        return True

    def can_show_model_solutions_to_student(self, student: User) -> bool:
        if self.course_instance.is_course_staff(student):
            return True
        if self.course_instance.is_on_lifesupport() or self.course_instance.is_archived():
            return False
        if not student.is_authenticated:
            return False

        from .reveal_states import ExerciseRevealState # pylint: disable=import-outside-toplevel
        state = ExerciseRevealState(self, student)
        return self.active_model_solutions_reveal_rule.is_revealed(state)

    def get_submission_draft(self, user_profile: UserProfile) -> Optional['SubmissionDraft']:
        """
        Returns the active submission draft for the user, if it exists.
        """
        return user_profile.submission_drafts.filter(
            exercise=self,
            active=True,
        ).first()

    def set_submission_draft(self, user_profile: UserProfile, submission_data: Any) -> None:
        """
        Creates a submission draft for the user, or updates an existing one.
        """
        user_profile.submission_drafts.update_or_create(
            exercise=self,
            defaults={
                'active': True,
                'submission_data': submission_data,
            },
        )

    def unset_submission_draft(self, user_profile: UserProfile) -> None:
        """
        Deactivates the active submission draft for the user, if it exists.
        """
        user_profile.submission_drafts.filter(
            exercise=self,
            active=True,
        ).update(active=False)


class LTIExercise(BaseExercise):
    """
    Exercise launched by LTI or optionally amending A+ protocol with LTI data.
    """
    lti_service = DefaultForeignKey(LTIService,
        verbose_name=_('LABEL_LTI_SERVICE'),
        on_delete=models.CASCADE,
    )
    context_id = models.CharField(
        verbose_name=_('LABEL_CONTEXT_ID'),
        max_length=128,
        blank=True,
        help_text=_('LTI_EXERCISE_CONTEXT_ID_HELPTEXT'),
    )
    resource_link_id = models.CharField(
        verbose_name=_('LABEL_RESOURCE_LINK_ID'),
        max_length=128,
        blank=True,
        help_text=_('LTI_EXERCISE_RESOURCE_LINK_ID_HELPTEXT'),
    )
    resource_link_title = models.CharField(
        verbose_name=_('LABEL_RESOURCE_LINK_TITLE'),
        max_length=128,
        blank=True,
        help_text=_('LTI_EXERCISE_RESOURCE_LINK_TITLE_HELPTEXT'),
    )
    aplus_get_and_post = models.BooleanField(
        verbose_name=_('LABEL_APLUS_GET_AND_POST'),
        default=False,
        help_text=_('LTI_EXERCISE_APLUS_GET_AND_POST_HELPTEXT'),
    )
    open_in_iframe = models.BooleanField(
        verbose_name=_('LABEL_OPEN_IN_IFRAME'),
        default=False,
        help_text=_('LTI_EXERCISE_OPEN_IN_IFRAME_HELPTEXT'),
    )

    class Meta:
        verbose_name = _('MODEL_NAME_LTI_EXERCISE')
        verbose_name_plural = _('MODEL_NAME_LTI_EXERCISE_PLURAL')

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        super().clean()
        # If service_url is defined and is an absolute URL, it must be in the
        # same domain as the LTI service.
        # Relative URLs are joined to the URL of the LTI service.
        if self.service_url:
            uri = urlsplit(self.service_url)
            if uri.netloc:
                if uri.netloc != urlsplit(self.lti_service.url).netloc:
                    raise ValidationError({
                        'service_url': _('LTI_EXERCISE_ERROR_SERVICE_URL_DOMAIN_MUST_MATCH_LTI_SERVICE'),
                    })
                # Save only the URL path in the database without the domain
                self.service_url = uri._replace(scheme='', netloc='').geturl()

    def load(
            self,
            request: HttpRequest,
            students: List[UserProfile],
            url_name: str = "exercise",
            ordinal: Optional[int] = None,
            ) -> ExercisePage:
        if not self.lti_service.enabled:
            messages.error(request, _('LTI_EXERCISE_ERROR_EXTERNAL_LTI_SERVICE_DISABLED'))
            raise PermissionDenied("The LTI service is disabled.")

        if self.aplus_get_and_post:
            return super().load(request, students, url_name=url_name, ordinal=ordinal)

        if not students:
            return ExercisePage(self)

        language = get_language()
        url = self.get_service_url(language)
        lti = self._get_lti(students[0].user, students, request)

        # Render launch button.
        page = ExercisePage(self)
        page.content = self.content
        template = loader.get_template('external_services/_launch.html')
        page.content += template.render({
            'service': self.lti_service,
            'service_label': self.lti_service.menu_label,
            'url': url,
            'parameters': lti.sign_post_parameters(url),
            'parameters_hash': lti.get_checksum_of_parameters(only_user_and_course_level_params=True),
            'exercise': self,
            'is_course_staff': self.course_instance.is_course_staff(request.user),
            'site': '/'.join(url.split('/')[:3]),
        })
        return page

    def _get_lti(self, user, students, request, add=None):
        try:
            return CustomStudentInfoLTIRequest(
                self.lti_service,
                user,
                students,
                self.course_instance,
                request,
                self.resource_link_title or self.lti_service.menu_label or self.name,
                self.context_id or None,
                self.resource_link_id or "aplusexercise{:d}".format(self.id or 0),
                add,
                exercise=self,
            )
        except PermissionDenied: # pylint: disable=try-except-raise
            raise

    def get_load_url( # pylint: disable=too-many-arguments
            self,
            language: str,
            request: HttpRequest,
            students: List[UserProfile],
            url_name: str = "exercise",
            ordinal: Optional[int] = None,
            ) -> str:
        url = super().get_load_url(language, request, students, url_name, ordinal)
        if self.lti_service and students:
            lti = self._get_lti(students[0].user, [], request)
            return lti.sign_get_query(url)
        return url

    def modify_post_parameters(self, data, files, user, students, request, url): # pylint: disable=too-many-arguments
        literals = {key: str(val[0]) for key,val in data.items()}
        lti = self._get_lti(user, students, request, add=literals)
        data.update(lti.sign_post_parameters(url))

    def get_service_url(self, language):
        url = super().get_service_url(language)
        if url and url.startswith('//') or '://' in url:
            return url
        return self.lti_service.get_final_url(url)

    @property
    def can_regrade(self):
        # the LTI protocol does not support regrading in the A+ way
        # (A+ would upload a submission to the service and expect it to be graded)
        return False


class StaticExercise(BaseExercise):
    """
    Static exercises are used for storing submissions on the server, but not automatically
    assessing them. Static exercises may be retrieved by other services through the API.

    Chapters should be used for non submittable content.

    Should be deprecated as a contradiction to A+ ideology.
    """
    exercise_page_content = models.TextField(
        verbose_name=_('LABEL_EXERCISE_PAGE_CONTENT'),
    )
    submission_page_content = models.TextField(
        verbose_name=_('LABEL_SUBMISSION_PAGE_CONTENT'),
    )

    class Meta:
        verbose_name = _('MODEL_NAME_STATIC_EXERCISE')
        verbose_name_plural = _('MODEL_NAME_STATICE_EXERCISE_PLURAL')

    def load(
            self,
            request: HttpRequest,
            students: List[UserProfile],
            url_name: str = "exercise",
            ordinal: Optional[int] = None,
            ) -> ExercisePage:
        page = ExercisePage(self)
        page.content = self.exercise_page_content
        return page

    def grade(self, submission, request=None, no_penalties=False, url_name="exercise"):
        page = ExercisePage(self)
        page.content = self.submission_page_content
        page.is_accepted = True
        return page

    def _is_empty(self):
        return not bool(self.exercise_page_content)

    @property
    def can_regrade(self):
        return False


def build_upload_dir(instance, filename):
    """
    Returns the path to a directory where the attachment file should be saved.
    This is called every time a new ExerciseWithAttachment model is created.

    @param instance: the ExerciseWithAttachment object
    @param filename: the actual name of the submitted file
    @return: a path where the file should be stored, relative to MEDIA_ROOT directory
    """
    return "course_instance_{:d}/exercise_attachment_{:d}/{}".format(
        instance.course_instance.id,
        instance.id,
        safe_file_name(filename)
    )


class ExerciseWithAttachment(BaseExercise):
    """
    ExerciseWithAttachment is an exercise type where the exercise instructions
    are stored locally and the exercise will be graded by sending an additional
    attachment to the grader together with other POST data. The exercise page
    will contain a submission form for the files the user should submit if the
    files to be submitted are defined. Otherwise the instructions must contain
    the submission form.

    Could be deprecated as a contradiction to A+ purist ideology.
    """
    files_to_submit = models.CharField(
        verbose_name=_('LABEL_FILES_TO_SUBMIT'),
        max_length=200,
        blank=True,
        help_text=_('EXERCISE_WITH_ATTACHMENT_FILES_TO_SUBMIT_HELPTEXT'),
    )
    attachment = models.FileField(
        verbose_name=_('LABEL_ATTACHMENT'),
        upload_to=build_upload_dir,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_EXERCISE_WITH_ATTACHMENT')
        verbose_name_plural = _('MODEL_NAME_EXERCISE_WITH_ATTACHMENT_PLURAL')

    def get_files_to_submit(self):
        """
        Returns a list of the file names that user should submit with this exercise.
        """
        if len(self.files_to_submit.strip()) == 0:
            return []
        files = self.files_to_submit.split("|")
        return [filename.strip() for filename in files]

    def load(
            self,
            request: HttpRequest,
            students: List[UserProfile],
            url_name: str = "exercise",
            ordinal: Optional[int] = None,
            ) -> ExercisePage:
        page = ExercisePage(self)
        page.content = self.content

        # Adds the submission form to the content if there are files to be
        # submitted. A template is used to avoid hard-coded HTML here.
        if self.get_files_to_submit():
            template = loader.get_template('exercise/model/_file_submit_form.html')
            context = {'files' : self.get_files_to_submit()}
            page.content += template.render(context)

        return page

    def modify_post_parameters(self, data, files, user, students, request, url): # pylint: disable=too-many-arguments
        """
        Adds the attachment file to post parameters.
        """
        files['content_0'] = (
            os.path.basename(self.attachment.path),
            open(self.attachment.path, "rb") # pylint: disable=consider-using-with
        )


def _delete_file(sender, instance, **kwargs): # pylint: disable=unused-argument
    """
    Deletes exercise attachment file after the exercise in database is removed.
    """
    default_storage.delete(instance.attachment.path)


def _clear_cache(sender, instance, **kwargs): # pylint: disable=unused-argument
    """
    Clears parent's cached html if any.
    """
    if instance.parent:
        ExerciseCache.invalidate(instance.parent)


post_delete.connect(_delete_file, ExerciseWithAttachment)
post_save.connect(_clear_cache, LearningObject)


class ExerciseTask(models.Model):
    """
    Asynchronous background tasks related to exercises.
    The task queue is implemented with Celery.
    For the time being this means ongoing mass regrade runs.
    """
    TASK_TYPE = Enum([
        ('REGRADE', 'regrade', _('REGRADE')),
    ])
    exercise = DefaultForeignKey('BaseExercise',
        verbose_name=_('LABEL_EXERCISE'),
        on_delete=models.CASCADE,
    )
    task_type = models.CharField(
        verbose_name=_('LABEL_TASK_TYPE'),
        max_length=32,
        choices=TASK_TYPE.choices,
        default=TASK_TYPE.REGRADE,
    )
    task_id = models.CharField(
        verbose_name=_('LABEL_TASK_ID'),
        max_length=128,
        blank=False,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_EXERCISE_TASK')
        verbose_name_plural = _('MODEL_NAME_EXERCISE_TASK_PLURAL')
        constraints = [models.UniqueConstraint(fields=['exercise', 'task_type'], name='one_task_type_per_exercise')]
