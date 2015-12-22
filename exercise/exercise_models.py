import datetime
import hashlib
import hmac

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_delete
from django.template import loader, Context
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _

from course.models import CourseModule, LearningObjectCategory
from inheritance.models import ModelWithInheritance
from lib.helpers import update_url_params, safe_file_name, roman_numeral
from userprofile.models import UserProfile

from .protocol.aplus import load_exercise_page, load_feedback_page
from .protocol.exercise_page import ExercisePage


class LearningObject(ModelWithInheritance):
    """
    All learning objects inherit this model.
    """
    STATUS_READY = 'ready'
    STATUS_UNLISTED = 'unlisted'
    STATUS_HIDDEN = 'hidden'
    STATUS_MAINTENANCE = 'maintenance'
    STATUS_CHOICES = (
        (STATUS_READY, _("Ready")),
        (STATUS_UNLISTED, _("Unlisted in table of contents")),
        (STATUS_HIDDEN, _("Hidden from non course staff")),
        (STATUS_MAINTENANCE, _("Maintenance")),
    )
    status = models.CharField(max_length=32,
        choices=STATUS_CHOICES, default=STATUS_READY)
    category = models.ForeignKey(LearningObjectCategory, related_name="learning_objects")
    course_module = models.ForeignKey(CourseModule, related_name="learning_objects")
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children')
    order = models.IntegerField(default=1)
    url = models.CharField(max_length=255,
        validators=[RegexValidator(regex="^[\w\-\.]*$")],
        help_text=_("Input an URL identifier for this object."))
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True,
        help_text=_("Internal description is not presented on site."))
    use_wide_column = models.BooleanField(default=False,
        help_text=_("Remove the third info column for more space."))
    service_url = models.URLField(blank=True)
    content = models.TextField(blank=True)
    content_head = models.TextField(blank=True)
    content_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        app_label = "exercise"
        ordering = ['course_module', 'order', 'id']
        unique_together = ['course_module', 'parent', 'url']

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        course_instance_error = ValidationError({
            'category':_('Course_module and category must belong to the same course instance.')
        })
        try:
            if (self.course_module.course_instance != self.category.course_instance):
                raise course_instance_error
        except (LearningObjectCategory.DoesNotExist, CourseModule.DoesNotExist):
            raise course_instance_error
        if self.parent and (self.parent.course_module != self.course_module
                or self.parent.id == self.id):
            raise ValidationError({
                'parent':_('Cannot select parent from another course module.')
            })
        RESERVED = ("submissions", "plain", "info")
        if self.url in RESERVED:
            raise ValidationError({
                'url':_("Taken words include: {}").format(", ".join(RESERVED))
            })

    def __str__(self):
        if self.course_instance.content_numbering == 1:
            number = self.number()
            if self.course_instance.module_numbering == 1:
                return "{:d}{} {}".format(self.course_module.order,
                    number, self.name)
                return "{} {}".format(number[1:], self.name)
        elif self.course_instance.content_numbering == 2:
            return "{} {}".format(roman_numeral(self.order, self.name))
        return self.name

    def number(self):
        if self.parent:
            return "{}.{:d}".format(self.parent.number(), self.order)
        return ".{:d}".format(self.order)

    @property
    def course_instance(self):
        return self.course_module.course_instance

    def is_submittable(self):
        return False

    def is_empty(self):
        return False

    def is_open(self, when=None):
        return self.course_module.is_open(when=when)

    def is_after_open(self, when=None):
        return self.course_module.is_after_open(when=when)

    def next(self):
        return self.course_module._children().next(self)

    def previous(self):
        return self.course_module._children().previous(self)

    def flat_learning_objects(self, with_sub_markers=True):
        return self.course_module._children().flat(self, with_sub_markers)

    def parent_list(self):
        parents = self.course_module._children().parents(self)
        return parents[:-1]

    def get_path_parts(self):
        return [n.url for n in self.course_module._children().parents(self)]

    def get_path(self):
        return '/'.join(self.get_path_parts())

    def get_url(self, name):
        instance = self.course_instance
        return reverse(name, kwargs={
            "course": instance.course.url,
            "instance": instance.url,
            "module": self.course_module.url,
            "exercise_path": self.get_path(),
        })

    def get_absolute_url(self):
        return self.get_url("exercise")

    def get_submission_list_url(self):
        return self.get_url("submission-list")

    def get_load_url(self, request, students, url_name="exercise"):
        return self.service_url

    def load(self, request, students, url_name="exercise"):
        """
        Loads the learning object page.
        """
        if self.id and self.content \
                and self.course_instance.ending_time < timezone.now():
            page = ExercisePage(self)
            page.is_loaded = True
            page.content_head = self.content_head
            page.content = self.content
        else:
            page = load_exercise_page(request, self.get_load_url(
                request, students, url_name), self)
            if self.id and (not self.content_time or \
                    self.content_time + datetime.timedelta(days=3) < timezone.now()):
                self.content_time = timezone.now()
                self.content_head = page.head
                self.content = page.content
                self.save()
        return page


class CourseChapter(LearningObject):
    """
    Chapters can offer and organize learning material as one page chapters.
    """
    generate_table_of_contents = models.BooleanField(default=False)

    def is_empty(self):
        return not (self.service_url or self.generate_table_of_contents)


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

    class Meta:
        app_label = 'exercise'

    def clean(self):
        """
        Validates the model before saving (standard method used in Django admin).
        """
        super().clean()
        if self.points_to_pass > self.max_points:
            raise ValidationError({
                'points_to_pass':_("Points to pass cannot be greater than max_points.")
            })

    def is_submittable(self):
        return True

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
            deviation = self.one_has_deadline_deviation(students)
            if deviation and when <= deviation.get_new_deadline():
                return True
        return False

    def one_has_deadline_deviation(self, students):
        deviation = None
        for profile in students:
            for d in self.deadlineruledeviation_set.filter(submitter=profile):
                if not deviation\
                        or d.get_new_deadline() > deviation.get_new_deadline():
                    deviation = d
        return deviation

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

    def one_has_submissions(self, students):
        if self.max_submissions == 0:
            return True
        for profile in students:
            if self.get_submissions_for_student(profile, True).count() \
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
        if self.course_instance.ending_time < timezone.now():
            warnings.append(_('The course is archived. Exercises are offline.'))
            success = False
        else:
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

        warnings = list(str(warning) for warning in warnings)
        return success, warnings

    def get_total_submitter_count(self):
        return UserProfile.objects \
            .filter(submissions__exercise=self) \
            .distinct().count()

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

    def get_load_url(self, request, students, url_name="exercise"):
        if self.id:
            student_str, hash_key = self.get_async_hash(students)
            return self._build_service_url(request, url_name, reverse(
                "async-new", kwargs={
                    "exercise_id": self.id if self.id else 0,
                    "student_ids": student_str,
                    "hash_key": hash_key
                }
            ))
        else:
            return self.service_url

    def grade(self, request, submission,
            no_penalties=False, url_name="exercise"):
        """
        Loads the exercise feedback page.
        """
        url = self._build_service_url(request, url_name, reverse(
            "async-grade", kwargs={
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

    def _build_service_url(self, request, url_name, submission_url):
        """
        Generates complete URL with added parameters to the exercise service.
        """
        params = {
            "max_points": self.max_points,
            "submission_url": request.build_absolute_uri(submission_url),
            "post_url": request.build_absolute_uri(
                str(self.get_url(url_name))),
        }
        return update_url_params(self.service_url, params)


class StaticExercise(BaseExercise):
    """
    Static exercises are used for storing submissions on the server, but not automatically
    assessing them. Static exercises may be retrieved by other services through the API.
    """
    exercise_page_content = models.TextField()
    submission_page_content = models.TextField()

    def load(self, request, students, url_name="exercise"):
        page = ExercisePage(self)
        page.content = self.exercise_page_content
        return page

    def grade(self, request, submission,
            no_penalties=False, url_name="exercise"):
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

    def load(self, request, students, url_name="exercise"):
        page = ExercisePage(self)
        page.content = self.content

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


def _delete_file(sender, instance, **kwargs):
    """
    Deletes exercise attachment file after the exercise in database is removed.
    """
    default_storage.delete(instance.attachment.path)
post_delete.connect(_delete_file, ExerciseWithAttachment)
