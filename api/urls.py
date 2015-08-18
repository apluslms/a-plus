from django.conf.urls import patterns, include, url
from tastypie.api import Api

from course.api import CourseResource, CourseInstanceResource, \
    CourseInstanceSummaryResource, CourseModuleResource
from exercise.api import LearningObjectResource, ExerciseResource, \
    SubmissionResource, SubmissionContentResource
from userprofile.api import UserProfileResource


api = Api(api_name='v1')

api.register(UserProfileResource())

api.register(CourseResource())
api.register(CourseInstanceResource())
api.register(CourseInstanceSummaryResource())
api.register(CourseModuleResource())
api.register(LearningObjectResource())

api.register(ExerciseResource())
api.register(SubmissionResource())
api.register(SubmissionContentResource())

urlpatterns = patterns('',
    url(r'^', include(api.urls)),
)
