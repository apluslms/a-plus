# Python
import simplejson
import urllib
import urllib2
import hmac
import hashlib
from datetime import datetime, timedelta

# Django 
from django.db import models
from django.db.models.aggregates import Avg, Max, Count
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django import forms
from django.conf import settings
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _
from django.template import loader, Context

# A+
from inheritance.models import ModelWithInheritance
from course.models import *
from lib import MultipartPostHandler
from lib.fields import PercentField
from exercise.exercise_page import ExercisePage
from userprofile.models import UserProfile

class CourseModule(models.Model):
    """ 
    CourseModule objects connect learning objects to logical sets of each other and 
    course instances. They also contain information about the opening times and 
    deadlines for exercises. 
    """
    name                    = models.CharField(max_length=255)
    points_to_pass          = models.PositiveIntegerField(default=0)
    
    # A textual introduction to this exercise round
    introduction            = models.TextField(blank=True)
    
    # Relations
    course_instance         = models.ForeignKey(CourseInstance, related_name=u"course_modules")
    
    # Fields related to the opening of the rounds
    opening_time            = models.DateTimeField(default=datetime.now)
    closing_time            = models.DateTimeField(default=datetime.now)
    
    def get_exercises(self):
        return BaseExercise.objects.filter(course_module=self)
    
    """
    Functionality related to early bonuses has been disabled. The following lines
    are commented out so that they can be restored later if necessary.
    
    # Settings related to early submission bonuses
    early_submissions_allowed= models.BooleanField(default=False)
    early_submissions_start = models.DateTimeField(default=datetime.now, blank=True, null=True)
    early_submission_bonus  = PercentField(default=0.1, 
        help_text=_("Multiplier of points to reward, as decimal. 0.1 = 10%"))
    """
    # Settings that can be used to allow late submissions to exercises
    late_submissions_allowed= models.BooleanField(default=False)
    late_submission_deadline= models.DateTimeField(default=datetime.now)
    late_submission_penalty = PercentField(default=0.5, 
        help_text=_("Multiplier of points to reduce, as decimal. 0.1 = 10%"))
    
    def is_late_submission_open(self):
        return self.late_submissions_allowed and \
            self.closing_time <= datetime.now() <= self.late_submission_deadline
    
    def is_open(self):
        return self.opening_time <= datetime.now() <= self.closing_time
    
    def is_after_open(self):
        """
        Returns True if current time is past the round opening time.
        """
        return self.opening_time <= datetime.now()

    def __unicode__(self):
        return self.name
    
    def get_breadcrumb(self):
        """ 
        Returns a list of tuples containing the names and URL 
        addresses of parent objects and self. 
        """
        return self.course_instance.get_breadcrumb()
    
    class Meta:
        app_label           = 'exercise'
        ordering            = ['closing_time', 'id']


class LearningObjectCategory(models.Model):
    name = models.CharField(max_length=35)
    description = models.TextField(blank=True)
    points_to_pass = models.PositiveIntegerField(default=0)

    course_instance = models.ForeignKey(CourseInstance,
        related_name=u"categories")

    hidden_to = models.ManyToManyField(
            UserProfile,
            related_name="hidden_categories",
            blank=True,
            null=True)

    class Meta:
        unique_together = ("name", "course_instance")

    def __unicode__(self):
        return self.name + u" -- " + unicode(self.course_instance)

    def is_hidden_to(self, profile):
        return profile in self.hidden_to.all()

    def set_hidden_to(self, profile, hide=True):
        if hide and not self.is_hidden_to(profile):
            self.hidden_to.add(profile)
        elif not hide and self.is_hidden_to(profile):
            self.hidden_to.remove(profile)


class LearningObject(ModelWithInheritance):
    # The order for sorting the exercises within an exercise round
    order                   = models.IntegerField(default=0)
    
    # Instruction related fields
    name                    = models.CharField(max_length=255)
    description             = models.TextField(blank=True)
    instructions            = models.TextField(blank=True)

    # TODO: deprecated
    # verify_exists is deprecated in Django 1.4 and removed in Django 1.5 because of security issues
    # However, in Django 1.3.0, it defaults to True, which is undesired, so we must have verify_exists=False with
    # this version of Django
    service_url             = models.URLField(verify_exists=False, blank=True)
    
    # Relations
    course_module          = models.ForeignKey(CourseModule, related_name="learning_objects")
    category               = models.ForeignKey(LearningObjectCategory,
                             related_name="learning_objects")

    def clean(self):
        course_instance_error = ValidationError("course_module and category "
                                                "must relate to the same "
                                                "CourseInstance object")

        try:
            if (self.course_module.course_instance
                != self.category.course_instance):
                raise course_instance_error
        except (LearningObjectCategory.DoesNotExist,
                CourseModule.DoesNotExist):
            raise course_instance_error

    def get_course_instance(self):
        return self.course_module.course_instance
    course_instance = property(get_course_instance)


class BaseExercise(LearningObject):
    # Switch for giving assistants permission to grade this exercise
    allow_assistant_grading = models.BooleanField(default=False)
    
    # Submission related fields
    min_group_size          = models.PositiveIntegerField(default=1)
    max_group_size          = models.PositiveIntegerField(default=1)
    max_submissions         = models.PositiveIntegerField(default=10)
    max_points              = models.PositiveIntegerField(default=100)
    points_to_pass          = models.PositiveIntegerField(default=40)

    def get_deadline(self):
        return self.course_module.closing_time
    
    def get_page(self, submission_url):
        """ 
        Retrieves the page for this exercise from the exercise service. 
        
        @param submission_url: the submission url where the service may return submissions
        @return: an ExercisePage object created from data retrieved from exercise service 
        """
        
        # Build the URL with a callback address, max points etc.
        url             = self.build_service_url(submission_url)
        
        opener          = urllib2.build_opener()
        page_content    = opener.open(url, timeout=20).read()
        
        return ExercisePage(self, page_content)
    
    
    def submit(self, submission):
        """ 
        This method sends the given submission to the exercise service 
        along with the files related to the submission. 
        """
        
        # Make sure that this is the correct exercise for the submission
        assert self.id == submission.exercise.id
        
        # Create an empty list for HTTP request parameters
        post_params             = []
        
        # Parameters are appended to the list as key, value tuples. 
        # Using tuples makes it possible to add two values for the same key.
        for (key, value) in submission.submission_data:
            post_params.append( (key, value) )
        
        # Then the files are appended as key, file handle tuples
        for submitted_file in submission.files.all():
            param_name          = submitted_file.param_name
            file_handle         = open(submitted_file.file_object.path, "rb")
            post_params.append( (param_name, file_handle) )
        
        # Allow to make necessary modifications to POST parameters
        self.modify_post_params(post_params)

        # Build the service URL, which contains maximum points for this exercise
        # and a callback URL to which the service may return the grading
        url                     = self.build_service_url( submission.get_callback_url() )
        
        opener                  = urllib2.build_opener(MultipartPostHandler.MultipartPostHandler)
        response_body           = opener.open(url.encode('ascii'), post_params, timeout=50).read()
        
        # Close all opened file handles
        for (key, value) in post_params:
            if type(value) == file:
                value.close()
        
        return ExercisePage(self, response_body)
    
    def modify_post_params(self, post_params):
        """
        Allows to modify POST parameters before they are sent to the grader.
        @param post_params: original POST parameters    
        """
        pass

    def is_open(self):
        """ 
        Returns True if submissions are allowed for this exercise. 
        """
        return self.course_module.is_open()
    
    def is_submission_allowed(self, students):
        """
        Returns True or False based whether the submission 
        to this exercise is allowed or not based on the parameters.
        
        @param students: the students who are submitting this exercise
        @return: boolean indicating if submissions should be accepted
        @return: errors as a list of strings
        """
        from exercise.submission_models import Submission
        
        errors              = []
        submissions         = Submission.objects.distinct().filter(exercise=self,
                                                                   submitters__in=students)
        
        # Check if the submissions are restricted or if the students have used too many of them
        submissions_left    = self.max_submissions == 0 or \
                                submissions.count() < self.max_submissions
        
        # Check if the number of students is allowed for this exercise
        allowed_group_size  = self.min_group_size <= students.count() <= self.max_group_size
        
        if not submissions_left:
            if students.count() == 1:
                errors.append( 'You have already submitted this exercise %d times.' % submissions.count())
            else:
                errors.append( 'This group has already submitted this exercise %d times.' % submissions.count())

        # Check if the exercise is open.
        # Submissions by superusers, staff, course teachers and course instance
        # assistants are still allowed.
        if (not self.is_open()
            and not self.is_late_submission_allowed()
            and not (
                students.count() == 1 and (
                    students[0].user.is_superuser
                    or students[0].user.is_staff
                    or self.course_module.course_instance.course.is_teacher(
                        students[0]
                    )
                    or self.course_module.course_instance.is_assistant(
                        students[0]
                    ))
                )):
            errors.append('This exercise is not open for submissions.')
        
        if not allowed_group_size:
            errors.append(_('This exercise can be submitted in groups of %d to %d students.') \
                          % (self.min_group_size, self.max_group_size) + " " + \
                          _('The size of your current group is %d.') \
                          % students.count())
        
        success             = len(errors) == 0
        return success, errors
    
    def is_late_submission_allowed(self):
        return self.course_module.late_submissions_allowed
    
    def get_late_submission_penalty(self):
        return self.course_module.late_submission_penalty
    
    def build_service_url(self, submission_url):
        """
        Generates and returns a complete URL with added parameters to the exercise service.
        
        @param submission_url: the URL where the service may return grading details
        """
        full_url        = settings.BASE_URL + submission_url
        
        params          = {"max_points"     : self.max_points,
                           "submission_url" : full_url,
                           }
        
        # If there is already a question mark in the url, use ampersand as delimiter. Otherwise 
        # use question mark.
        delimiter       = ("?", "&")["?" in self.service_url]
        
        url             = self.service_url + delimiter + urllib.urlencode(params)
        return url
    
    def get_submissions_for_student(self, userprofile):
        """ 
        Returns all submissions for the given user profile for this exercise.
        
        @param userprofile: the user's profile whose submissions to find
        @return: a QuerySet of matching submissions 
        """
        return userprofile.submissions.filter(exercise=self)
    
    def __unicode__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("exercise.views.view_exercise", kwargs={"exercise_id": self.id})
    
    def get_submission_parameters_for_students(self, students):
        '''
        @param students: a QuerySet of UserProfiles
        @return: a string with UserProfile ids and a hash
        @return: a string with UserProfile ids and a hash
        '''
        student_str     = "-".join( str(userprofile.id) for userprofile in students )
        identifier      = "%s.%d" % (student_str, self.id)
        hash            = hmac.new(settings.SECRET_KEY, 
                                   msg=identifier, 
                                   digestmod=hashlib.sha256).hexdigest()
        return student_str, hash
    
    def get_submission_url_for_students(self, students):
        '''
        Creates and returns an URL where a submission can be made for the given students
        
        @param students: a QuerySet of UserProfile objects for the students submitting the exercise
        @return: an URL where submissions are accepted for the students
        '''
        student_str, hash = self.get_submission_parameters_for_students(students)
        
        return reverse("exercise.async_views.new_async_submission", 
                       kwargs={"student_ids": student_str,
                               "exercise_id": self.id,
                               "hash": hash})
    
    def __get_summary(self):
        """
        Returns a dictionary which has summarized statistics of this exercise. The dictionary is
        generated only once and saved into a private field to improve performance with subsequent
        calls.
        
        @return: a dictionary keys: submission_count, average_grade, average_submissions and
        submitter_count
        """
        if not hasattr(self, "temp_summary"):
            submission_count        = self.submissions.count()
            submitter_count         = UserProfile.objects.distinct().filter(submissions__exercise=self).count()
            
            average_grade           = UserProfile.objects.distinct().filter(submissions__exercise=self).annotate(best_grade=Max('submissions__grade')).aggregate(average_grade=Avg('best_grade'))["average_grade"]
            average_submissions     = UserProfile.objects.distinct().filter(submissions__exercise=self).annotate(submission_count=Count('submissions')).aggregate(avg_submissions=Avg('submission_count'))["avg_submissions"]
            
            if average_grade == None:
                average_grade       = 0
            if average_submissions == None:
                average_submissions = 0
            
            self.temp_summary       = {"submission_count"   : submission_count,
                                       "average_grade"      : average_grade,
                                       "submitter_count"    : submitter_count,
                                       "average_submissions": average_submissions,
                                       }
        return self.temp_summary
    
    summary = property(__get_summary)
    
    @classmethod
    def get_exercise(cls, *args, **kwargs):
        """
        Returns an object matching the given query parameters as an 
        instance of the exercise's actual class, not the super class.
        """
        return cls.objects.get(*args, **kwargs).as_leaf_class()
    
    def get_breadcrumb(self):
        """ 
        Returns a list of tuples containing the names and url 
        addresses of parent objects and self. 
        """
        crumb       = self.course_module.get_breadcrumb()
        crumb_tuple = (str(self), self.get_absolute_url())
        crumb.append(crumb_tuple)
        return crumb
    
    def can_edit(self, userprofile):
        """
        Returns a boolean value indicating if the given user profile is allowed to edit 
        this exercise. Superusers and teachers are allowed to edit exercises.
        
        @param userprofile: the user profile whose permissions are checked
        @return: True if is allowed, False otherwise
        """
        if userprofile.user.is_superuser:
            return True
        
        if self.course_module.course_instance.course.is_teacher(userprofile):
            return True
        
        return False
    
    class Meta:
        app_label   = 'exercise'
        ordering    = ['course_module__closing_time', 'course_module', 'order', 'id']


class AsynchronousExercise(BaseExercise):
    """ 
    Asynchronous exercises are used when the assessment service does not grade the 
    exercises immediately after submission. Instead, the exercise system will call 
    a submission URL after assessing and generating feedback. 
    """
    pass


class SynchronousExercise(BaseExercise):
    """ 
    Synchronous exercises are submitted and assessed during a single HTTP request.
    The exercise service will respond to POST requests with a number of points and 
    a feedback for the student. 
    """
    pass


class StaticExercise(BaseExercise):
    """ 
    Static exercises are used for storing submissions on the server, but not automatically 
    assessing them. Static exercises may be retrieved by other services through the API. 
    """
    
    exercise_page_content   = models.TextField()
    submission_page_content = models.TextField()
    
    
    def get_page(self, submission_url=None):
        """
        @param submission_url: the submission url where the service may return submissions
        @return: an ExercisePage object created from data retrieved from exercise service 
        """
        page            = ExercisePage(self)
        page.content    = self.exercise_page_content
        return page
    
    def submit(self, submission):
        page            = ExercisePage(self)
        page.content    = self.submission_page_content
        page.is_accepted= True
        return page

def build_upload_dir(instance, filename):
    """ 
    Returns the path where the attachement should be saved.    
    
    @param instance: the ExerciseWithAttachment object
    @param filename: the actual name of the submitted file
    @return: a path where the file should be stored, relative to MEDIA_ROOT directory 
    """

    return "exercise_attachments/exercise_%d/%s" % (instance.id, filename)

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
    attachment     = models.FileField(upload_to=build_upload_dir)

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

    def modify_post_params(self, post_params):
        """
        Adds the attachment to POST request. It will be added before the first original
        item of the file array with the same field name or if no files are found it
        will be added as first parameter using name file[].
        @param post_params: original POST parameters, assumed to be a list
        """

        found = False
        for i in range(len(post_params)):
            if type(post_params[i][1]) == file and post_params[i][0].endswith("[]"):
                handle = open(self.attachment.path, "rb")
                post_params.insert(i, (post_params[i][0], handle))
                found = True
                break

        if not found:
            post_params.insert(0, ('file[]', open(self.attachment.path, "rb")))

    def get_page(self, submission_url=None):
        """
        @param submission_url: the submission url where the service may return submissions
        @return: an ExercisePage containing the exercise instructions and possibly a submit form 
        """
        page            = ExercisePage(self)
        page.content    = self.instructions

        # Adds the submission form to the content if there are files to be submitted.
        # A template is used to avoid hard-coded HTML here.
        if self.get_files_to_submit():
            template = loader.get_template('exercise/_file_submit_form.html')
            context = Context({'files' : self.get_files_to_submit()})
            page.content += template.render(context)

        return page


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
    exercise = models.ForeignKey(BaseExercise,
                                 related_name="%(class)ss")
    submitter = models.ForeignKey(UserProfile)

    class Meta:
        abstract = True
        unique_together = ["exercise", "submitter"]
        app_label = 'exercise'


class DeadlineRuleDeviation(SubmissionRuleDeviation):
    extra_minutes = models.IntegerField()

    class Meta(SubmissionRuleDeviation.Meta):
        pass

    def get_extra_time(self):
        return timedelta(minutes=self.extra_minutes)

    def get_new_deadline(self):
        return self.get_normal_deadline() + self.get_extra_time()

    def get_normal_deadline(self):
        return self.exercise.get_deadline()


class MaxSubmissionsRuleDeviation(SubmissionRuleDeviation):
    extra_submissions = models.IntegerField()

    class Meta(SubmissionRuleDeviation.Meta):
        pass
