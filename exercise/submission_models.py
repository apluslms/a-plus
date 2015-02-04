# Django
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseBadRequest, HttpResponse
from django.db.models.signals import post_init, pre_save
from django.core.urlresolvers import reverse
from django.core.files.storage import default_storage
from django.db.models.signals import post_delete

# A+
from exercise import exercise_models
from lib import MultipartPostHandler
from lib.fields import JSONField
from lib.helpers import get_random_string
from userprofile.models import UserProfile

# Python 2.6+
from datetime import datetime, timedelta
import simplejson, os


class Submission(models.Model):
    _status_choices         = (("initialized", _(u"Initialized")),
                               ("waiting", _(u"Waiting")),
                               ("ready", _(u"Ready")),
                               ("error", _(u"Error")))

    submission_time         = models.DateTimeField(auto_now_add=True)
    hash                    = models.CharField(max_length=32, default=get_random_string)

    # Relations
    exercise                = models.ForeignKey(exercise_models.BaseExercise, 
                                                related_name="submissions")
    submitters              = models.ManyToManyField(UserProfile, 
                                                     related_name="submissions")
    grader                  = models.ForeignKey(UserProfile, 
                                                related_name="graded_submissions", 
                                                blank=True, 
                                                null=True)

    # Grading specific
    feedback                = models.TextField(blank=True)
    assistant_feedback      = models.TextField(blank=True)
    status                  = models.CharField(max_length=32, 
                                               default=_status_choices[0][0], 
                                               choices=_status_choices)
    grade                   = models.IntegerField(default=0)
    grading_time            = models.DateTimeField(blank=True, null=True)

    # Points received from assessment, before scaled to grade
    service_points          = models.IntegerField(default=0)
    service_max_points      = models.IntegerField(default=0)

    # Additional submission and grading data
    submission_data         = JSONField(blank=True)
    grading_data            = JSONField(blank=True)

    def add_submitter(self, user_profile):
        """ 
        Adds a new student to the submitters of this exercise.

        @param user_profiles: a UserProfile that is submitting the exercise
        """
        self.submitters.add(user_profile)

    def add_submitters(self, user_profiles):
        """
        Adds students for this submission.

        @param user_profiles: an iterable with UserProfile objects
        """
        for u_p in user_profiles:
            self.add_submitter(u_p)

    def add_files(self, files):
        """ 
        Adds the given files to this submission as SubmittedFile objects.
        @param files: a QueryDict containing files from a POST request 
        """
        for key in files:
            for uploaded_file in files.getlist(key):
                userfile                = SubmittedFile()
                userfile.file_object    = uploaded_file
                userfile.param_name     = key

                # Add the SubmittedFile to the submission
                self.files.add(userfile)

    def check_user_permission(self, profile):
        """ 
        Checks if the given user is allowed to access this submission.
        Superusers and staff are allowed to access all submissions, course
        personnel is allowed to access submissions for that course and students
        are allowed to access their own submissions.

        @param profile: UserProfile model 
        """

        # Superusers and staff are allowed to view all submissions
        if profile.user.is_superuser or profile.user.is_staff:
            return True

        # Check if the user has submitted this submission him/herself
        if profile in self.submitters.all():
            return True

        # Check if the user belongs to the course staff
        if self.get_course_instance().is_staff(profile):
            return True

        return False

    def get_course(self):
        return self.get_course_instance().course

    def get_course_instance(self):
        return self.exercise.course_module.course_instance

    def set_points(self, points, max_points, no_penalties=False):
        """ 
        Sets the points and maximum points for this submissions. If the given
        maximum points are different than the ones for the exercise this
        submission is for, the points will be scaled.

        The method also checks if the submission is late and if it is, by
        default applies the late_submission_penalty set for the
        exercise.course_module. If no_penalties is True, the penalty is not
        applied.

        @param points: the amount of points received from assessment
        @param max_points: the total amount of points available in assessment
        @param no_penalties: If True, the possible late_submission_penalty is
        not applied.
        """

        # The given points must be between zero and max points
        assert 0 <= points <= max_points
        # If service max points is zero, then exercise max points must be zero
        # too because otherwise adjusted_grade would be ambiguous.
        assert not (max_points == 0 and self.exercise.max_points != 0)

        self.service_points = points
        self.service_max_points = max_points

        # Scale the given points to the maximum points for the exercise
        if max_points > 0:
            adjusted_grade = (1.0 * self.exercise.max_points
                              * points / max_points)
        else:
            adjusted_grade = 0.0

        # Check if this submission was done late. If it was, reduce the points
        # with late submission penalty. No less than 0 points are given. This
        # is not done if no_penalties is True.
        if not no_penalties and self.is_submitted_late():
            adjusted_grade -= (adjusted_grade
                               * self.exercise.get_late_submission_penalty())

        self.grade = round(adjusted_grade)

        # Finally check that the grade is in bounds after all the hardcore
        # math!
        assert 0 <= self.grade <= self.exercise.max_points

    def is_submitted_late(self):
        if not self.id and not self.submission_time:
            # The submission is not saved and the submission_time field is not
            # set yet so this method takes the liberty to set it.
            self.submission_time = datetime.now()

        return self.exercise.course_module.is_expired() and \
               not self.exercise.is_open_for(students=self.submitters.all(),
                                             when=self.submission_time)
                 

    def set_grading_data(self, grading_dict):
        self.grading_data = grading_dict

    def submitter_string(self):
        # TODO: Write a version of this method that has the names wrapped in
        # html anchors pointing to the profile page of the user.
        """
        Returns a comma separated string containing full names and possibly the
        student ids of all the submitters of this submission.
        """

        submitter_strs = []
        for profile in self.submitters.all():
            if profile.student_id:
                student_id_str = " (%s)" % profile.student_id
            else:
                student_id_str = ""
            submitter_strs.append(profile.user.get_full_name()
                                  + student_id_str)

        return ", ".join(submitter_strs)

    def __unicode__(self):
        return str(self.id)

    # Status methods. The status indicates whether this submission is just
    # created, waiting for grading, ready or erroneous.
    def _set_status(self, new_status):
        self.status = new_status

    def set_waiting(self):
        self._set_status("waiting")

    def is_graded(self):
        return self.status == "ready"

    def set_ready(self):
        self.grading_time = datetime.now()
        self._set_status("ready")
        for hook in self.exercise.course_instance.course_hook.filter(hook_type="post-grading"):
            hook.trigger({"submission_id":self.id})

    def set_error(self):
        self._set_status("error")

    def get_absolute_url(self):
        return reverse("exercise.views.view_submission", kwargs={"submission_id": self.id})

    def get_callback_url(self):
        identifier = "s.%d.%d.%s" % (self.id, self.exercise.id, self.hash)
        return reverse("exercise.async_views.grade_async_submission", 
                       kwargs={"submission_id": self.id,
                               "hash": self.hash})

    def get_staff_url(self):
        return reverse("exercise.staff_views.inspect_exercise_submission",
            kwargs={"submission_id": self.id})

    def submit_to_service(self, files=None):
        # Get the exercise as an instance of its real leaf class
        exercise = self.exercise.as_leaf_class()

        return exercise.submit(self)

    def get_breadcrumb(self):
        """ 
        Returns a list of tuples containing the names and url 
        addresses of parent objects and self. 
        """
        crumb           = self.exercise.get_breadcrumb()
        crumb_tuple     = (_("Submission"), self.get_absolute_url())
        crumb.append(crumb_tuple)
        return crumb

    class Meta:
        app_label       = 'exercise'
        ordering        = ['-submission_time']


def build_upload_dir(instance, filename):
    """ 
    Returns the path to a directory where the file should be saved. 
    This is called every time a new SubmittedFile model is created.
    The file paths include IDs for the course instance, the exercise, 
    the users who submitted the file and the submission the file belongs to.

    @param instance: the new SubmittedFile object
    @param filename: the actual name of the submitted file
    @return: a path where the file should be stored, relative to MEDIA_ROOT directory 
    """
    exercise        = instance.submission.exercise
    course_instance = exercise.course_module.course_instance

    # Collect submitter ids in a list of strings
    submitter_ids   = [str(profile.id) for profile in instance.submission.submitters.all()]

    return "submissions/course_instance_%d/exercise_%d/users_%s/submission_%d/%s" % \
        (course_instance.id,
         exercise.id,
         "-".join(submitter_ids), # Join submitter ids using dash as a separator
         instance.submission.id,
         filename)


class SubmittedFile(models.Model):
    """ 
    Submitted file represents a file submitted by the student as a solution 
    to an exercise. Submitted files are always linked to a certain submission 
    through a foreign key relation. The files are stored on the disk while 
    SubmittedFile models are stored in the database. 
    """

    submission              = models.ForeignKey(Submission, related_name="files")
    param_name              = models.CharField(max_length=128)
    file_object             = models.FileField(upload_to=build_upload_dir, max_length=255)

    def _get_filename(self):
        """ Returns the actual name of the file on the disk. """
        return os.path.basename(self.file_object.path)

    # filename property is used to hide the logic in _get_filename
    filename = property(_get_filename)

    def get_absolute_url(self):
        """ 
        Returns the url for downloading this file. The url contains both the id of this model and the 
        name of the file on the disk. Only the file id is used in the URL pattern and the view that returns
        the file. 
        """
        view_url = reverse('exercise.views.view_submitted_file', kwargs={"submitted_file_id": self.id})
        return view_url + self.filename

    class Meta:
        app_label           = 'exercise'


def _delete_file(sender, instance, **kwargs):
    """ 
    This function deletes the actual files referenced by SubmittedFile
    objects after the objects are deleted from database. 
    """
    default_storage.delete(instance.file_object.path)

# Connect signal to deleting a SubmittedFile
post_delete.connect(_delete_file, SubmittedFile)

