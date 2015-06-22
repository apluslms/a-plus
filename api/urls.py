from django.conf.urls import patterns, include, url
from tastypie.api import Api

from course.api import CourseInstanceSummaryResource
from course.api import CourseResource, CourseInstanceResource
from exercise.api import ExerciseResource, CourseModuleResource, \
  SubmissionResource, SubmissionContentResource, LearningObjectResource
from userprofile.api import UserProfileResource


api = Api(api_name='v1')
api.register(CourseResource())
api.register(CourseInstanceResource())
api.register(UserProfileResource())
api.register(ExerciseResource())
api.register(CourseModuleResource())
api.register(SubmissionResource())
api.register(SubmissionContentResource())
api.register(LearningObjectResource())
api.register(CourseInstanceSummaryResource())

urlpatterns = patterns('',
    url(r'^', include(api.urls)),
)
