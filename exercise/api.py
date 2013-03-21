# Tastypie
from tastypie.resources import ModelResource, Resource, ALL
from api_permissions import *
from tastypie.authentication import OAuthAuthentication, OAuthAuthentication
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization
from tastypie import fields

# A+
from userprofile.models import UserProfile
from exercise_models import LearningObject, BaseExercise, CourseModule, CourseInstance
from submission_models import Submission, SubmittedFile
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

