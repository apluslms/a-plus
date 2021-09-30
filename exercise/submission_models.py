import itertools
import logging
import os
import json
from typing import IO, Dict, Iterable, List, Tuple, TYPE_CHECKING

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models, DatabaseError
from django.db.models.signals import post_delete
from django.http.request import HttpRequest
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _
from mimetypes import guess_type
from exercise.protocol.exercise_page import ExercisePage

from authorization.models import JWTAccessible
from authorization.object_permissions import register_jwt_accessible_class
from lib.fields import JSONField, PercentField
from lib.helpers import (
    get_random_string,
    query_dict_to_list_of_tuples,
    pairs_to_dict,
    safe_file_name,
    Enum,
)
from lib.models import UrlMixin
from userprofile.models import UserProfile
from . import exercise_models


logger = logging.getLogger('aplus.exercise')


class SubmissionQuerySet(models.QuerySet):
    def annotate_submitter_points(
            self,
            field_name: str = 'total',
            revealed_ids: Iterable[int] = None,
            ) -> 'SubmissionQuerySet':
        """
        Annotates the total points earned by the submitter in the exercise to
        the queryset. Chain after `values` and before `order_by` to ensure one
        points row per submitter and exercise.

        The result will be assigned to a field named by `field_name`.

        Provide `revealed_ids`, if you want to hide unrevealed points from the
        queryset.
        """
        # Building a case expression for calculating the total points. There
        # are 4 cases:
        # 1) If revealed_ids was provided, and the exercise id is not in it,
        #    return 0.
        # 2) If a submission has the force_exercise_points flag set to True,
        #    return that submission's points.
        # 3) If the grading_mode field of the exercise is set to LAST, return
        #    the points of the latest submission.
        # 4) In any other case, return the points of the best submission.
        cases = []
        if revealed_ids is not None:
            cases.append(
                models.When(
                    ~models.Q(exercise__in=revealed_ids),
                    then=0,
                )
            )
        cases.append(
            models.When(
                forced_points__isnull=False,
                then=models.F('forced_points'),
            )
        )
        cases.append(
            models.When(
                exercise__grading_mode=exercise_models.BaseExercise.GRADING_MODE.LAST,
                then=models.Subquery(
                    self.filter(
                        exercise=models.OuterRef('exercise_id'),
                        submitters=models.OuterRef('submitters__id'),
                    )
                    .order_by('-submission_time')
                    .values('grade')[:1]
                ),
            )
        )
        return (
            self.alias(
                forced_points=models.Max('grade', filter=models.Q(force_exercise_points=True)),
            )
            .annotate(**{
                field_name: models.Case(*cases, default=models.Max('grade')),
            })
        )


class SubmissionManager(JWTAccessible["Submission"], models.Manager):
    _queryset_class = SubmissionQuerySet

    def get_queryset(self):
        return super().get_queryset()\
            .prefetch_related('submitters')

    def create_from_post(self, exercise, submitters, request):

        submission_data_list = [
                (key, value) for (key, value) in query_dict_to_list_of_tuples(request.POST)
                if key != '__aplus__'
        ]
        try:
            meta_data_dict = json.loads(request.POST.get('__aplus__', '{}'))
        except json.JSONDecodeError:
            raise ValueError("The content of the field __aplus__ is not valid json")
        if 'lang' not in meta_data_dict:
            meta_data_dict['lang'] = get_language()

        try:
            new_submission = Submission.objects.create(
                exercise=exercise,
                submission_data=submission_data_list,
                meta_data=meta_data_dict,
            )
            new_submission.submitters.set(submitters)
        except DatabaseError as error:
            logger.exception("Failed to create submission: %s %s",
                request.user.username, exercise);
            raise DatabaseError from error
        try:
            new_submission.add_files(request.FILES)
        except DatabaseError as error:
            logger.exception("Failed to save submitted files: %s %s",
                request.user.username, exercise);
            new_submission.delete()
            raise DatabaseError from error
        return new_submission

    def exclude_errors(self):
        return self.exclude(status__in=(
            Submission.STATUS.ERROR,
            Submission.STATUS.REJECTED,
        ))

    def get_combined_enrollment_submission_data(self, user):
        """Retrieve the user's submissions to enrollment exercises and combine
        their submission data into a single dictionary.
        The most recent value (based on submission time) is used for data keys
        that are present in multiple submissions.

        The values in the returned dictionary are lists since some form inputs
        accept multiple values (e.g., checkboxes). (The original submission_data
        is stored as a list of key-value pairs, but multiple pairs may repeat
        the same key.)
        """
        submissions = Submission.objects.filter(
            exercise__status__in=(
                exercise_models.LearningObject.STATUS.ENROLLMENT,
                exercise_models.LearningObject.STATUS.ENROLLMENT_EXTERNAL
            ),
            submitters__user__id=user.id
        ).order_by('submission_time').only('submission_data')[:10]
        # Retrieve the ten latest submissions since older submissions likely
        # do not have any useful data.
        enrollment_data = {}
        keyfunc = lambda t: t[0] # the key in a key-value pair
        for sbms in submissions:
            # submission_data should be a list of key-value pairs, but
            # nothing guarantees it in the database level.
            # Checkbox inputs may produce multiple values for the same key, thus
            # the list of pairs may use the same key in different pairs.
            # For each submission, group the submission data by the keys so that
            # multiple values can be preserved for a key when all submissions
            # are combined.
            single_sbms_grouped_data = {} # dict maps keys to the list of one or more values
            try:
                for key, pairs in itertools.groupby(
                        sorted(sbms.submission_data, key=keyfunc),
                        key=keyfunc):
                    single_sbms_grouped_data[key] = [val for k, val in pairs]

                # Update the combined enrollment submission data.
                # Later submissions overwrite previous values for the same keys.
                # The keys are combined from many submissions, but the value list
                # for one key always originates from one submission.
                enrollment_data.update(single_sbms_grouped_data)
            except Exception:
                # submission_data was not a list of pairs
                pass
        return enrollment_data


@register_jwt_accessible_class("submission")
class Submission(UrlMixin, models.Model):
    """
    A submission to some course exercise from one or more submitters.
    """
    STATUS = Enum([
        ('INITIALIZED', 'initialized', _('STATUS_INITIALIZED')),
        ('WAITING', 'waiting', _('STATUS_WAITING')),
        ('READY', 'ready', _('STATUS_READY')), # graded normally
        ('ERROR', 'error', _('STATUS_ERROR')),
        ('REJECTED', 'rejected', _('STATUS_REJECTED')), # missing fields etc
        ('UNOFFICIAL', 'unofficial', _('STATUS_UNOFFICIAL')),
        # unofficial: graded after the deadline or after exceeding the submission limit
    ])
    submission_time = models.DateTimeField(
        verbose_name=_('LABEL_SUBMISSION_TIME'),
        auto_now_add=True,
    )
    hash = models.CharField(
        verbose_name=_('LABEL_HASH'),
        max_length=32,
        default=get_random_string,
    )

    # Relations
    exercise = models.ForeignKey(exercise_models.BaseExercise,
        verbose_name=_('LABEL_EXERCISE'),
        on_delete=models.CASCADE,
        related_name="submissions")
    submitters = models.ManyToManyField(UserProfile,
        verbose_name=_('LABEL_SUBMITTERS'),
        related_name="submissions")
    grader = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_GRADER'),
        on_delete=models.SET_NULL,
        related_name="graded_submissions",
        blank=True, null=True,
    )

    # Grading and feedback
    feedback = models.TextField(
        verbose_name=_('LABEL_FEEDBACK'),
        blank=True,
    )
    assistant_feedback = models.TextField(
        verbose_name=_('LABEL_STAFF_FEEDBACK'),
        blank=True,
    )
    status = models.CharField(
        verbose_name=_('LABEL_STATUS'),
        max_length=32,
        choices=STATUS.choices, default=STATUS.INITIALIZED,
    )
    grade = models.IntegerField(
        verbose_name=_('LABEL_GRADE'),
        default=0,
    )
    grading_time = models.DateTimeField(
        verbose_name=_('LABEL_GRADING_TIME'),
        blank=True, null=True,
    )
    late_penalty_applied = PercentField(
        verbose_name=_('LABEL_LATE_PENALTY_APPLIED'),
        blank=True, null=True,
    )
    force_exercise_points = models.BooleanField(
        verbose_name=_('LABEL_FORCE_EXERCISE_POINTS'),
        default=False,
    )

    # Points received from assessment, before scaled to grade
    service_points = models.IntegerField(
        verbose_name=_('LABEL_SERVICE_POINTS'),
        default=0,
    )
    service_max_points = models.IntegerField(
        verbose_name=_('LABEL_SERVICE_MAX_POINTS'),
        default=0,
    )

    # Additional data
    submission_data = JSONField(
        verbose_name=_('LABEL_SUBMISSION_DATA'),
        blank=True,
    )
    grading_data = JSONField(
        verbose_name=_('LABEL_GRADING_DATA'),
        blank=True,
    )
    meta_data = JSONField(
        verbose_name=_('LABEL_META_DATA'),
        blank=True,
    )

    objects = SubmissionManager()

    class Meta:
        verbose_name = _('MODEL_NAME_SUBMISSION')
        verbose_name_plural = _('MODEL_NAME_SUBMISSION_PLURAL')
        app_label = 'exercise'
        ordering = ['-id']

    def __str__(self):
        return str(self.id)

    def ordinal_number(self):
        return self.submitters.first().submissions.exclude_errors().filter(
            exercise=self.exercise,
            submission_time__lt=self.submission_time
        ).count() + 1

    def is_submitter(self, user):
        return user and user.is_authenticated and \
            self.submitters.filter(id=user.userprofile.id).exists()

    def add_files(self, files):
        """
        Adds the given files to this submission as SubmittedFile objects.

        @param files: a QueryDict containing files from a POST request
        """
        for key in files:
            for uploaded_file in files.getlist(key):
                self.files.create(
                    file_object=uploaded_file,
                    param_name=key,
                )

    def load(self, request: HttpRequest, allow_submit: bool = True) -> ExercisePage:
        """
        Loads the submission page, i.e. the exercise form with the submitted
        answers filled in. Not the same as the graded form, which is stored in
        `feedback`.

        The `allow_submit` argument determines if the submit button will be
        shown on the page.
        """
        # Load the exercise page and parse its contents
        submitters = list(self.submitters.all())
        page = self.exercise.as_leaf_class().load(
            request,
            submitters,
            url_name='exercise',
            ordinal=self.ordinal_number(),
        )
        if self.submission_data:
            data = pairs_to_dict(self.submission_data)
            page.populate_form(field_values=data, allow_submit=allow_submit)

        return page

    def get_post_parameters(
            self,
            request: HttpRequest, url: str
            ) -> Tuple[Dict[str, List[str]], Dict[str, Tuple[str, IO]]]:
        """
        Produces submission data for POST as (data_dict, files_dict).
        """
        if self.submission_data:
            self._data = pairs_to_dict(self.submission_data)
        else:
            self._data = {}

        self._files = {}
        for file in self.files.all().order_by("id"):
            # Requests supports only one file per name in a multipart post.
            self._files[file.param_name] = (
                file.filename,
                open(file.file_object.path, "rb")
            )

        students = list(self.submitters.all())
        if self.is_submitter(request.user):
            user = request.user
        else:
            user = students[0].user if students else None
        self.exercise.as_leaf_class().modify_post_parameters(
            self._data, self._files, user, students, request, url)
        return (self._data, self._files)

    def clean_post_parameters(self):
        for key in self._files.keys():
            self._files[key][1].close()
        del self._files
        del self._data

    def set_points(self, points, max_points, no_penalties=False):
        """
        Sets the points and maximum points for this submissions. If the given
        maximum points are different than the ones for the exercise this
        submission is for, the points will be scaled.

        The method also checks if the submission is late and if it is, by
        default applies the late_submission_penalty set for the
        exercise.course_module. If no_penalties is True, the penalty is not
        applied.
        """
        exercise = self.exercise

        # Evade bad max points in remote service.
        if max_points == 0 and points > 0:
            max_points = exercise.max_points

        # The given points must be between zero and max points
        assert 0 <= points <= max_points

        # If service max points is zero, then exercise max points must be zero
        # too because otherwise adjusted_grade would be ambiguous.
        # Disabled: Teacher is always responsible the exercise can be passed.
        #assert not (max_points == 0 and self.exercise.max_points != 0)

        self.service_points = points
        self.service_max_points = max_points
        self.late_penalty_applied = None

        # Scale the given points to the maximum points for the exercise
        if max_points > 0:
            adjusted_grade = (1.0 * exercise.max_points * points / max_points)
        else:
            adjusted_grade = 0.0

        if not no_penalties:
            timing,_ = exercise.get_timing(self.submitters.all(), self.submission_time)
            if timing in (exercise.TIMING.LATE, exercise.TIMING.CLOSED_AFTER):
                self.late_penalty_applied = (
                    exercise.course_module.late_submission_penalty if
                    exercise.course_module.late_submissions_allowed else 0
                )
                adjusted_grade -= (adjusted_grade * self.late_penalty_applied)
            elif timing == exercise.TIMING.UNOFFICIAL:
                self.status = self.STATUS.UNOFFICIAL
            if self.exercise.no_submissions_left(self.submitters.all()):
                self.status = self.STATUS.UNOFFICIAL

        self.grade = round(adjusted_grade)

        # Finally check that the grade is in bounds after all the math.
        assert 0 <= self.grade <= self.exercise.max_points

    def scale_grade_to(self, percentage):
        percentage = float(percentage)/100
        self.grade = round(max(self.grade*percentage,0))
        self.grade = min(self.grade,self.exercise.max_points)

    def set_waiting(self):
        self.status = self.STATUS.WAITING

    def set_ready(self):
        self.grading_time = timezone.now()
        if self.status != self.STATUS.UNOFFICIAL or self.force_exercise_points:
            self.status = self.STATUS.READY

        # Fire set hooks.
        for hook in self.exercise.course_module.course_instance \
                .course_hooks.filter(hook_type="post-grading"):
            hook.trigger({
                "submission_id": self.id,
                "exercise_id": self.exercise.id,
                "course_id": self.exercise.course_module.course_instance.id,
                "site": settings.BASE_URL,
            })

    def set_rejected(self):
        self.status = self.STATUS.REJECTED

    def set_error(self):
        self.status = self.STATUS.ERROR

    @property
    def is_graded(self):
        return self.status in (self.STATUS.READY, self.STATUS.UNOFFICIAL)

    @property
    def lang(self):
        try:
            return self.meta_data.get('lang', None)
        except AttributeError:
            # Handle cases where database includes null or non dictionary json
            return None

    ABSOLUTE_URL_NAME = "submission"

    def get_url_kwargs(self):
        return dict(submission_id=self.id, **self.exercise.get_url_kwargs())

    def get_inspect_url(self):
        return self.get_url("submission-inspect")


class SubmissionDraft(models.Model):
    """
    An incomplete submission that is saved automatically before the user
    submits it. A user can have exactly one draft per exercise instead of
    multiple. The one draft is continuously updated as the user types.
    """
    timestamp = models.DateTimeField(
        verbose_name=_('LABEL_TIMESTAMP'),
        auto_now=True,
    )
    exercise = models.ForeignKey(exercise_models.BaseExercise,
        verbose_name=_('LABEL_EXERCISE'),
        on_delete=models.CASCADE,
        related_name='submission_drafts'
    )
    submitter = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_SUBMITTER'),
        on_delete=models.CASCADE,
        related_name='submission_drafts'
    )
    submission_data = JSONField(
        verbose_name=_('LABEL_SUBMISSION_DATA'),
        blank=True,
    )
    # This flag is set to False when the student makes an actual submission.
    # This way the draft doesn't have to be deleted and recreated every time
    # the student makes a submission and then starts a new draft.
    active = models.BooleanField(
        verbose_name=_('LABEL_ACTIVE'),
        default=True,
    )

    if TYPE_CHECKING:
        objects: models.Manager['SubmissionDraft']
        id: models.AutoField

    class Meta:
        verbose_name = _('MODEL_NAME_SUBMISSION_DRAFT')
        verbose_name_plural = _('MODEL_NAME_SUBMISSION_DRAFT_PLURAL')
        app_label = 'exercise'
        unique_together = ('exercise', 'submitter')

    def load(self, request: HttpRequest) -> ExercisePage:
        """
        Loads the draft page, i.e. the exercise form with the user's
        incomplete answers filled in.
        """
        enrollment = self.exercise.course_instance.get_enrollment_for(request.user)
        if enrollment and enrollment.selected_group:
            students = list(enrollment.selected_group.members.all())
        else:
            students = [request.user.userprofile]

        page = self.exercise.as_leaf_class().load(
            request,
            students,
            url_name='exercise',
        )
        if self.submission_data:
            data = pairs_to_dict(self.submission_data)
            # Format the timestamp so that it can be used in Javascript's Date constructor
            timestamp = str(int(self.timestamp.timestamp() * 1000))
            page.populate_form(field_values=data, data_values={'draft-timestamp': timestamp}, allow_submit=True)

        return page


def build_upload_dir(instance, filename):
    """
    Returns the path to a directory where a file should be saved.
    This is called every time a new SubmittedFile model is created.

    @param instance: the new SubmittedFile object
    @param filename: the actual name of the submitted file
    @return: a path where the file should be stored, relative to MEDIA_ROOT directory
    """
    submission = instance.submission
    exercise = submission.exercise
    submitter_ids = [str(profile.id) for profile in submission.submitters.all().order_by("id")]
    return "course_instance_{:d}/submissions/exercise_{:d}/users_{}/submission_{:d}/{}".format(
        exercise.course_instance.id,
        exercise.id,
        "-".join(submitter_ids),
        submission.id,
        safe_file_name(filename)
    )


class SubmittedFile(UrlMixin, models.Model):
    """
    Represents a file submitted by the student as a solution to an exercise.
    Submitted files are always linked to a certain submission through a
    foreign key relation. The files are stored on the disk while models are
    stored in the database.
    """
    PASS_MIME = ( "image/jpeg", "image/png", "image/gif", "application/pdf", "application/zip" )
    submission = models.ForeignKey(Submission,
        verbose_name=_('LABEL_SUBMISSION'),
        on_delete=models.CASCADE,
        related_name="files",
    )
    param_name = models.CharField(
        verbose_name=_('LABEL_PARAM_NAME'),
        max_length=128,
    )
    file_object = models.FileField(
        verbose_name=('LABEL_FILE_OBJECT'),
        upload_to=build_upload_dir,
        max_length=255,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_SUBMITTED_FILE')
        verbose_name_plural = _('MODEL_NAME_SUBMITTED_FILE_PLURAL')
        app_label = 'exercise'

    @property
    def filename(self):
        """
        Returns the actual name of the file on the disk.
        """
        return os.path.basename(self.file_object.path)

    @property
    def exists(self):
        try:
            return bool(self.file_object.size)
        except OSError:
            return False

    def get_mime(self):
        return guess_type(self.file_object.path)[0]

    def is_passed(self):
        return self.get_mime() in SubmittedFile.PASS_MIME


    ABSOLUTE_URL_NAME = "submission-file"

    def get_url_kwargs(self):
        return dict(
            file_id=self.id,
            file_name=self.filename,
            **self.submission.get_url_kwargs())


def _delete_file(sender, instance, **kwargs):
    """
    Deletes the actual submission files after the submission in database is
    removed.
    """
    instance.file_object.delete(save=False)
post_delete.connect(_delete_file, SubmittedFile)
