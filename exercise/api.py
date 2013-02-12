# Django
from django.contrib.auth.models import User
from django.conf.urls.defaults import url

# Tastypie
from tastypie.resources import ModelResource, Resource, ALL
from api_permissions import *
from tastypie.authentication import OAuthAuthentication, OAuthAuthentication
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization
from tastypie import fields

# A+
from userprofile.models import UserProfile
from exercise_models import LearningObject, BaseExercise, CourseModule, CourseInstance
from exercise_summary import CourseSummary
from submission_models import Submission, SubmittedFile
from course.api import CourseInstanceResource
from api_permissions import SuperuserAuthorization

class LearningObjectResource(ModelResource):
    class Meta:
        queryset        = LearningObject.objects.all()
        resource_name   = 'learning_object'
        excludes        = []
        
        # In the first version GET (read only) requests are 
        # allowed and no authentication is required
        allowed_methods = ['get']
        authentication  = Authentication()
        authorization   = ReadOnlyAuthorization()


class ExerciseResource(ModelResource):
    submissions         = fields.ToManyField('exercise.api.SubmissionResource', 'submissions')
    
    class Meta:
        queryset        = BaseExercise.objects.all()
        resource_name   = 'exercise'
        excludes        = []
        
        # In the first version GET (read only) requests are 
        # allowed and no authentication is required
        allowed_methods = ['get']
        authentication  = Authentication()
        authorization   = ReadOnlyAuthorization()

class CourseModuleResource(ModelResource):
    learning_objects    = fields.ToManyField('exercise.api.LearningObjectResource', 'learning_objects')
    
    class Meta:
        queryset        = CourseModule.objects.all()
        resource_name   = 'coursemodule'
        excludes        = []
        
        # In the first version GET (read only) requests are 
        # allowed and no authentication is required
        allowed_methods = ['get']
        authentication  = Authentication()
        authorization   = ReadOnlyAuthorization()

class CourseInstanceOverallSummaryResource(Resource):

    class Meta:        
        object_class    = object
        allowed_methods = ['get']

    def obj_get(self, request=None, **kwargs):
        # TODO  return  summary containing scores from all users and for each
        #       user URI to the user specific results
        pass


class CourseInstanceSummaryResource(Resource):

    class Meta:
        resource_name           = 'course_results'
        object_class            = CourseSummary                
        allowed_methods         = ['get']
        include_resource_uri    = False
    
    #From: http://www.maykinmedia.nl/blog/2012/oct/2/nested-resources-tastypie/
    def override_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/user/(?P<user>\w[\w/-]*)/$' % 
                (self._meta.resource_name ),
                self.wrap_view('dispatch_user_results'),
                name='api_course_user'),
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/$' % 
                (self._meta.resource_name ),
                self.wrap_view('dispatch_overall'),
                name='api_course_overall'),
            url(r'^(?P<resource_name>%s)/$' % 
                (self._meta.resource_name ),
                self.wrap_view('dispatch_course_instances'),
                name='api_course_instances')            
        ]
    def dispatch_overall(self, request, **kwargs):
        return CourseInstanceOverallSummaryResource().dispatch(
            'detail', request, **kwargs)

    def dispatch_user_results(self, request, **kwargs):
        return CourseInstanceSummaryResource().dispatch(
            'detail', request, **kwargs)
    
    def dispatch_course_instances(self, request, **kwargs):
        return CourseInstanceResource().dispatch(
            'list', request, **kwargs)

    def obj_get(self, request=None, **kwargs): 
        results         = []
        course_instance = CourseInstance.objects.get(pk=kwargs["pk"])
        user            = User.objects.get(pk=kwargs["user"])
        course_summary  = CourseSummary(course_instance, user)
        for rnd in course_summary.round_summaries:
            exercise_summaries = []
            for ex_summary in rnd.exercise_summaries:
                tmp = {}
                tmp["exercise_id"] = ex_summary.exercise.id
                tmp["submission_count"] = ex_summary.submission_count
                tmp["completed_percentage"] = ex_summary.get_completed_percentage()
                exercise_summaries.append(tmp)
            results.append( { "exercise_round_id":rnd.exercise_round.id, 
                              "completed_percentage":rnd.get_completed_percentage(),
                              "closing_time": rnd.exercise_round.closing_time,
                              "exercise_summaries": exercise_summaries
                            } )                
        return results

    def dehydrate(self, bundle):        
        bundle.data["exercise_rounds"] = []
        for rnd in bundle.obj:
            bundle.data["exercise_rounds"].append(rnd)
        return bundle

class SubmissionResource(ModelResource):
    exercise            = fields.ToOneField('exercise.api.ExerciseResource', 'exercise')
    grader              = fields.ToOneField('userprofile.api.UserProfileResource', 'grader', null=True, blank=True)
    submitters          = fields.ToManyField('userprofile.api.UserProfileResource', 'submitters', null=True, blank=True)
    
    def dehydrate(self, bundle):
        """
        This method iterates over the URLs of the files submitted with each 
        submission and adds them in the file_urls lists of submissions.
        """
        file_urls       = []
        for file in bundle.obj.files.all():
            file_urls.append(file.get_absolute_url())
        bundle.data.update({"files": file_urls})
        return bundle
    
    class Meta:
        queryset        = Submission.objects.all()
        resource_name   = 'submission'
        excludes        = ['feedback']
        allowed_methods = ['get']
        include_absolute_url = True
        
        # Rules that enable filtering based on exercise, grader, submitter and grade.
        filtering = {
            "exercise": ('exact',),
            "grader": ('exact',),
            "submitters": ('exact',),
            "grade": ALL,
            "id": ALL
        }
        
        # In this version only superusers are allowed to access
        # submissions after being authenticated with OAuth
        authentication  = OAuthAuthentication()
        authorization   = SuperuserAuthorization()

