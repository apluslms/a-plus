from _io import TextIOWrapper
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.aggregates import Sum
from django.template import loader, Context
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _

from course.models import CourseInstance
from exercise.remote.connection import load_exercise_page, load_feedback_page
from exercise.remote.exercise_page import ExercisePage
from inheritance.models import ModelWithInheritance
from lib.fields import PercentField
from userprofile.models import UserProfile


class CourseModule(models.Model):
    """
    CourseModule objects connect learning objects to logical sets of each other
    and course instances. They also contain information about the opening times
    and deadlines for exercises. A module may also include a reference to
    study content. 
    """
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255,
                       validators=[RegexValidator(regex="^(?!teachers$)(?!user$)[\w\-\.]*$")],
                       help_text=_("Input an URL identifier for this module. Taken words include: teachers, user"))
    chapter = models.IntegerField(default=1)
    subchapter = models.IntegerField(default=1)
    points_to_pass = models.PositiveIntegerField(default=0)
    introduction = models.TextField(blank=True)
    course_instance = models.ForeignKey(CourseInstance, related_name="course_modules")
    opening_time = models.DateTimeField(default=datetime.now)
    closing_time = models.DateTimeField(default=datetime.now)
    content_url = models.URLField(blank=True)

    # early_submissions_allowed= models.BooleanField(default=False)
    # early_submissions_start = models.DateTimeField(default=datetime.now, blank=True, null=True)
    # early_submission_bonus  = PercentField(default=0.1,
    #   help_text=_("Multiplier of points to reward, as decimal. 0.1 = 10%"))
    
    late_submissions_allowed = models.BooleanField(default=False)
    late_submission_deadline = models.DateTimeField(default=datetime.now)
    late_submission_penalty = PercentField(default=0.5,
        help_text=_("Multiplier of points to reduce, as decimal. 0.1 = 10%"))

    class Meta:
        app_label = 'exercise'
        unique_together = ("course_instance", "url")
        ordering = ['closing_time', 'id']

    def __str__(self):
        return self.name + " / " + str(self.course_instance)

    def get_exercises(self):
        return BaseExercise.objects.filter(course_module=self)

    def is_open(self, when=None):
        when = when or datetime.now()
        return self.opening_time <= when <= self.closing_time

    def is_after_open(self, when=None):
        """
        Checks if current time is past the round opening time.
        """
        when = when or datetime.now()
        return self.opening_time <= when
    
    def is_late_submission_open(self, when=None):
        when = when or datetime.now()
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

    def get_absolute_url(self):
        instance = self.course_instance
        return reverse('exercise.views.view_module', kwargs={
            'course_url': instance.course.url,
            'instance_url': instance.url,
            'module_url': self.url
        })

    def get_breadcrumb(self):
        """
        Returns a list of tuples containing the names and URL
        addresses of parent objects and self.
        """
        crumb = self.course_instance.get_breadcrumb()
        crumb.append((self.name, self.get_absolute_url()))
        return crumb
        return self.course_instance.get_breadcrumb()


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
        app_label = 'exercise'
        unique_together = ("name", "course_instance")

    def __str__(self):
        return self.name + " / " + str(self.course_instance)

    def get_exercises(self):
        return BaseExercise.objects.filter(category=self)

    def get_maximum_points(self):
        if not hasattr(self, "_cached_max_points"):
            max_points = self.get_exercises().aggregate(max_points=Sum('max_points'))['max_points']
            self._cached_max_points = max_points or 0
        return self._cached_max_points

    def get_required_percentage(self):
        max_points = self.get_maximum_points()
        if max_points == 0:
            return 0
        else:
            return int(round(100.0 * self.points_to_pass / max_points))

    def is_hidden_to(self, user_profile):
        return self.hidden_to.filter(id=user_profile.id).exists()

    def set_hidden_to(self, user_profile, hide=True):
        if hide and not self.is_hidden_to(user_profile):
            self.hidden_to.add(user_profile)
        elif not hide and self.is_hidden_to(user_profile):
            self.hidden_to.remove(user_profile)


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
        app_label = 'exercise'
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
        when = when or datetime.now()
        return self.course_module.is_open(when=when)

    def one_has_access(self, students, when=None):
        """
        Checks if any of the users can submit taking the granted extra time
        in consideration.
        """
        when = when or datetime.now()
        module = self.course_module
        if module.is_open(when=when) \
        or module.is_late_submission_open(when=when):
            return True
        if self.course_module.is_after_open(when=when):
            for profile in students:
                deviation = DeadlineRuleDeviation.objects \
                    .filter(exercise=self, submitter=profile).first()
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
        deviation = MaxSubmissionsRuleDeviation.objects \
            .filter(exercise=self, submitter=user_profile).first()
        if deviation:
            return self.max_submissions + \
                deviation.extra_submissions
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

    def get_absolute_url(self):
        instance = self.course_module.course_instance
        return reverse("exercise.views.view_exercise", kwargs={
            "course_url": instance.course.url,
            "instance_url": instance.url,
            "exercise_id": self.id
        })

    def get_breadcrumb(self):
        """
        Returns a list of tuples containing the names and url
        addresses of parent objects and self.
        """
        crumb = self.course_module.get_breadcrumb()
        crumb_tuple = (str(self), self.get_absolute_url())
        crumb.append(crumb_tuple)
        return crumb

    def load(self, request, students):
        """
        Loads the exercise page.
        """
        return load_exercise_page(request, self, students)
    
    def grade(self, request, submission, no_penalties=False):
        """
        Loads the exercise feedback page.
        """
        return load_feedback_page(request, self, submission,
            no_penalties=no_penalties)

    def modify_post_parameters(self, post_params):
        """
        Allows to modify submission POST parameters before they are sent to
        the grader. Extending classes may implement this function.
        """
        pass


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

    def modify_post_parameters(self, post_params):
        """
        Adds the attachment to POST request. It will be added before the first original
        item of the file array with the same field name or if no files are found it
        will be added as first parameter using name file[].
        @param post_params: original POST parameters, assumed to be a list
        """
        found = False
        for i in range(len(post_params)):
            if isinstance(post_params[i][1], TextIOWrapper) and post_params[i][0].endswith("[]"):
                handle = open(self.attachment.path, "rb")
                post_params.insert(i, (post_params[i][0], handle))
                found = True
                break

        if not found:
            post_params.insert(0, ('file[]', open(self.attachment.path, "rb")))


class SubmissionRuleDeviation(models.Model):
    """
    An abstract model binding a user to an exercise stating that there is some
    kind of deviation from the normal submission boundaries, that is, special
    treatment related to the submissions of that particular user to that
    particular exercise.

    If there are many submitters submitting an exercise out of bounds of the
    default bounds, all of the submitters must have an allowing instance of
    SubmissionRuleDeviation subclass in order for the submission to be allowed.
    """
    exercise = models.ForeignKey(BaseExercise, related_name="%(class)ss")
    submitter = models.ForeignKey(UserProfile)

    class Meta:
        app_label = 'exercise'
        abstract = True
        unique_together = ["exercise", "submitter"]


class DeadlineRuleDeviation(SubmissionRuleDeviation):
    extra_minutes = models.IntegerField()

    class Meta(SubmissionRuleDeviation.Meta):
        pass

    def get_extra_time(self):
        return timedelta(minutes=self.extra_minutes)

    def get_new_deadline(self):
        return self.get_normal_deadline() + self.get_extra_time()

    def get_normal_deadline(self):
        return self.exercise.course_module.closing_time


class MaxSubmissionsRuleDeviation(SubmissionRuleDeviation):
    extra_submissions = models.IntegerField()

    class Meta(SubmissionRuleDeviation.Meta):
        pass
