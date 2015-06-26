import hashlib
import hmac
import urllib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.template import loader, Context
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _

from course.models import CourseModule, LearningObjectCategory
from inheritance.models import ModelWithInheritance
from userprofile.models import UserProfile

from .protocol.aplus import load_exercise_page, load_feedback_page
from .protocol.exercise_page import ExercisePage


class LearningObject(ModelWithInheritance):
    """
    All learning objects e.g. exercises inherit this model.
    """
    order = models.IntegerField(default=1)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    service_url = models.URLField(blank=True)
    course_module = models.ForeignKey(CourseModule, related_name="learning_objects")
    category = models.ForeignKey(LearningObjectCategory, related_name="learning_objects")

    class Meta:
        ordering = ['order', 'id']

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        course_instance_error = ValidationError(
            _("Course_module and category must belong to the same course instance."))
        try:
            if (self.course_module.course_instance != self.category.course_instance):
                raise course_instance_error
        except (LearningObjectCategory.DoesNotExist, CourseModule.DoesNotExist):
            raise course_instance_error

    @property
    def course_instance(self):
        return self.course_module.course_instance

    def get_absolute_url(self):
        instance = self.course_instance
        return reverse("learning_object", kwargs={
            "course_url": instance.course.url,
            "instance_url": instance.url,
            "exercise_id": self.id
        })


class BaseExercise(LearningObject):
    """
    The common parts for all exercises.
    """
    allow_assistant_grading = models.BooleanField(default=False)
    min_group_size = models.PositiveIntegerField(default=1)
    max_group_size = models.PositiveIntegerField(default=1)
    max_submissions = models.PositiveIntegerField(default=10)
    max_points = models.PositiveIntegerField(default=100)
    points_to_pass = models.PositiveIntegerField(default=40)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'exercise'
        ordering = ['course_module__closing_time', 'course_module', 'order', 'id']

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        if self.points_to_pass > self.max_points:
            return ValidationError(
                _("Points to pass cannot be greater than max_points."))

    def is_open(self, when=None):
        """
        Returns True if submissions are allowed for this exercise.
        """
        when = when or timezone.now()
        return self.course_module.is_open(when=when)

    def one_has_access(self, students, when=None):
        """
        Checks if any of the users can submit taking the granted extra time
        in consideration.
        """
        when = when or timezone.now()
        module = self.course_module
        if module.is_open(when=when) \
        or module.is_late_submission_open(when=when):
            return True
        if self.course_module.is_after_open(when=when):
            for profile in students:
                deviation = self.deadlineruledeviation_set \
                    .filter(submitter=profile).first()
                if deviation and when <= deviation.get_new_deadline():
                    return True
        return False

    def get_submissions_for_student(self, user_profile):
        return user_profile.submissions.filter(exercise=self)

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

    def one_has_submissions(self, students):
        if self.max_submissions == 0:
            return True
        for profile in students:
            if self.get_submissions_for_student(profile).count() \
                < self.max_submissions_for_student(profile):
                return True
        return False

    def is_submission_allowed(self, students):
        """
        Checks whether the submission to this exercise is allowed for the given
        users and generates list of warnings.

        @return: (success_flag, warning_message_list)
        """
        warnings = []

        if not self.one_has_access(students):
            warnings.append(
                _('This exercise is not open for submissions.'))
        
        if not (self.min_group_size <= len(students) <= self.max_group_size):
            warnings.append(
                _('This exercise can be submitted in groups of %(min)d to %(max)d students.'
                  'The size of your current group is %(size)d.') % {
                    'min': self.min_group_size,
                    'max': self.max_group_size,
                    'size': len(students),
                })

        if not self.one_has_submissions(students):
            warnings.append(
                _('You have used the allowed amount of submissions for this exercise.'))

        # The above problems will prevent the submission if users are not in
        # course staff. The problems below are always just notifications.
        success = len(warnings) == 0 \
            or all(self.course_instance.is_course_staff(p.user) for p in students)

        # If late submission is open, notify the student about point reduction.
        if self.course_module.is_late_submission_open():
            warnings.append(
                _('Deadline for the exercise has passed. Late submissions are allowed until'
                  '{date} but points are only worth {percent:d}%.').format(
                    date=date_format(self.course_module.late_submission_deadline),
                    percent=self.course_module.get_late_submission_point_worth(),
                ))

        return success, warnings

    def get_total_submitter_count(self):
        return UserProfile.objects \
            .filter(submissions__exercise=self) \
            .distinct().count()

    def get_breadcrumb(self):
        """
        Returns a list of tuples containing the names and url
        addresses of parent objects and self.
        """
        crumb = self.course_module.get_breadcrumb()
        crumb_tuple = (str(self), self.get_absolute_url())
        crumb.append(crumb_tuple)
        return crumb

    def get_async_hash(self, students):
        student_str = "-".join(
            sorted(str(userprofile.id) for userprofile in students)
        )
        identifier = "{}.{:d}".format(student_str, self.id)
        hash_key = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            msg=identifier.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        return student_str, hash_key.hexdigest()

    def load(self, request, students):
        """
        Loads the exercise page.
        """
        student_str, hash_key = self.get_async_hash(students)
        url = self._build_service_url(request, reverse(
            "exercise.async_views.new_async_submission", kwargs={
                "exercise_id": self.id,
                "student_ids": student_str,
                "hash_key": hash_key
            }))
        return load_exercise_page(request, url, self, students)
    
    def grade(self, request, submission, no_penalties=False):
        """
        Loads the exercise feedback page.
        """
        url = self._build_service_url(request, reverse(
            "exercise.async_views.grade_async_submission", kwargs={
                "submission_id": submission.id,
                "hash_key": submission.hash
            }))
        return load_feedback_page(request, url, self, submission,
            no_penalties=no_penalties)

    def modify_post_parameters(self, data, files):
        """
        Allows to modify submission POST parameters before they are sent to
        the grader. Extending classes may implement this function.
        """
        pass

    def _build_service_url(self, request, submission_url):
        """
        Generates complete URL with added parameters to the exercise service.
        """
        params = {
            "max_points": self.max_points,
            "submission_url": request.build_absolute_uri(submission_url),
        }
        delimiter = "&" if "?" in self.service_url else "?"
        return self.service_url + delimiter + urllib.parse.urlencode(params)


class StaticExercise(BaseExercise):
    """
    Static exercises are used for storing submissions on the server, but not automatically
    assessing them. Static exercises may be retrieved by other services through the API.
    """
    exercise_page_content = models.TextField()
    submission_page_content = models.TextField()

    def load(self, request, students):
        page = ExercisePage(self)
        page.content = self.exercise_page_content
        return page

    def grade(self, request, submission, no_penalties=False):
        page = ExercisePage(self)
        page.content = self.submission_page_content
        page.is_accepted = True
        return page


def build_upload_dir(instance, filename):
    """
    Returns the path to a directory where the attachment file should be saved.
    This is called every time a new ExerciseWithAttachment model is created.

    @param instance: the ExerciseWithAttachment object
    @param filename: the actual name of the submitted file
    @return: a path where the file should be stored, relative to MEDIA_ROOT directory
    """
    return "exercise_attachments/exercise_{:d}/{}".format(instance.id, filename)


class ExerciseWithAttachment(BaseExercise):
    """
    ExerciseWithAttachment is an exercise type where the exercise instructions
    are stored locally and the exercise will be graded by sending an additional
    attachment to the grader together with other POST data. The exercise page
    will contain a submission form for the files the user should submit if the
    files to be submitted are defined. Otherwise the instructions must contain
    the submission form.
    """
    files_to_submit = models.CharField(max_length=200, blank=True,
        help_text=_("File names that user should submit, use pipe character to separate files"))
    attachment = models.FileField(upload_to=build_upload_dir)

    class Meta:
        verbose_name_plural = "exercises with attachment"

    def get_files_to_submit(self):
        """
        Returns a list of the file names that user should submit with this exercise.
        """
        if len(self.files_to_submit.strip()) == 0:
            return []
        else:
            files = self.files_to_submit.split("|")
            return [filename.strip() for filename in files]

    def load(self, request, students):
        page = ExercisePage(self)
        page.content = self.instructions

        # Adds the submission form to the content if there are files to be
        # submitted. A template is used to avoid hard-coded HTML here.
        if self.get_files_to_submit():
            template = loader.get_template('exercise/model/_file_submit_form.html')
            context = Context({'files' : self.get_files_to_submit()})
            page.content += template.render(context)

        return page

    def modify_post_parameters(self, data, files):
        """
        Adds the attachment file to post parameters.
        """
        import os
        files['content_0'] = (
            os.path.basename(self.attachment.path),
            open(self.attachment.path, "rb")
        )
