import logging
import os

from django.core.files.storage import default_storage
from django.db import models, DatabaseError
from django.db.models.signals import post_delete
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from mimetypes import guess_type

from lib.fields import JSONField, PercentField
from lib.helpers import get_random_string, query_dict_to_list_of_tuples, \
    safe_file_name, Enum
from lib.models import UrlMixin
from userprofile.models import UserProfile
from . import exercise_models


logger = logging.getLogger('aplus.exercise')


class SubmissionManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset()\
            .prefetch_related('submitters')

    def create_from_post(self, exercise, submitters, request):
        new_submission = Submission.objects.create(
            exercise=exercise,
            submission_data=query_dict_to_list_of_tuples(request.POST)
        )
        new_submission.submitters = submitters
        try:
            new_submission.add_files(request.FILES)
        except DatabaseError:
            logger.exception("Failed to save submitted files: %s %s",
                request.user.username, exercise);
            new_submission.delete()
            return None
        return new_submission

    def exclude_errors(self):
        return self.exclude(status__in=(
            Submission.STATUS.ERROR,
            Submission.STATUS.REJECTED,
        ))


class Submission(UrlMixin, models.Model):
    """
    A submission to some course exercise from one or more submitters.
    """
    STATUS = Enum([
        ('INITIALIZED', 'initialized', _("Initialized")),
        ('WAITING', 'waiting', _("In grading")),
        ('READY', 'ready', _("Ready")), # graded normally
        ('ERROR', 'error', _("Error")),
        ('REJECTED', 'rejected', _("Rejected")), # missing fields etc
        ('UNOFFICIAL', 'unofficial', _("Unofficial")), # graded after closing
    ])
    submission_time = models.DateTimeField(auto_now_add=True)
    hash = models.CharField(max_length=32, default=get_random_string)

    # Relations
    exercise = models.ForeignKey(exercise_models.BaseExercise,
        related_name="submissions")
    submitters = models.ManyToManyField(UserProfile,
        related_name="submissions")
    grader = models.ForeignKey(UserProfile,
        related_name="graded_submissions", blank=True, null=True)

    # Grading and feedback
    feedback = models.TextField(blank=True)
    assistant_feedback = models.TextField(blank=True)
    status = models.CharField(max_length=32,
        choices=STATUS.choices, default=STATUS.INITIALIZED)
    grade = models.IntegerField(default=0)
    grading_time = models.DateTimeField(blank=True, null=True)
    late_penalty_applied = PercentField(blank=True, null=True)

    # Points received from assessment, before scaled to grade
    service_points = models.IntegerField(default=0)
    service_max_points = models.IntegerField(default=0)

    # Additional data
    submission_data = JSONField(blank=True)
    grading_data = JSONField(blank=True)

    objects = SubmissionManager()

    class Meta:
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
        return user and user.is_authenticated() and \
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

    def get_post_parameters(self, request, url):
        """
        Produces submission data for POST as (data_dict, files_dict).
        """
        self._data = {}
        for (key, value) in self.submission_data or {}:
            if key in self._data:
                self._data[key].append(value)
            else:
                self._data[key] = [ value ]

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
            self._data, self._files, user, students, request.get_host(), url)
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
        if self.status != self.STATUS.UNOFFICIAL:
            self.status = self.STATUS.READY

        # Fire set hooks.
        for hook in self.exercise.course_module.course_instance \
                .course_hooks.filter(hook_type="post-grading"):
            hook.trigger({ "submission_id": self.id })

    def set_rejected(self):
        self.status = self.STATUS.REJECTED

    def set_error(self):
        self.status = self.STATUS.ERROR

    @property
    def is_graded(self):
        return self.status in (self.STATUS.READY, self.STATUS.UNOFFICIAL)

    ABSOLUTE_URL_NAME = "submission"

    def get_url_kwargs(self):
        return dict(submission_id=self.id, **self.exercise.get_url_kwargs())

    def get_inspect_url(self):
        return self.get_url("submission-inspect")


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
    PASS_MIME = ( "image/jpeg", "image/png", "image/gif", "application/pdf" )
    submission = models.ForeignKey(Submission, related_name="files")
    param_name = models.CharField(max_length=128)
    file_object = models.FileField(upload_to=build_upload_dir, max_length=255)

    class Meta:
        app_label = 'exercise'

    @property
    def filename(self):
        """
        Returns the actual name of the file on the disk.
        """
        return os.path.basename(self.file_object.path)

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
    default_storage.delete(instance.file_object.path)
post_delete.connect(_delete_file, SubmittedFile)
