from django.conf.urls import patterns, include, url
from tastypie.api import Api

from course.api.v1 import CourseResource, CourseInstanceResource, \
    CourseInstanceSummaryResource, CourseModuleResource
from exercise.api.v1 import LearningObjectResource, ExerciseResource, \
    SubmissionResource, SubmissionContentResource
from userprofile.api.v1 import UserProfileResource

###
# WARNING: this is deprecated v1 API. It will be reomved in the future.
# Do not make additions to this api, instead use new API.
###

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
