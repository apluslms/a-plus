from django.conf.urls.defaults import *
from tastypie.api import Api
from course.api import CourseResource, CourseInstanceResource
from userprofile.api import UserProfileResource
from exercise.api import ExerciseResource, CourseModuleResource, SubmissionResource, \
    LearningObjectResource

api = Api(api_name='v1')
api.register(CourseResource())
api.register(CourseInstanceResource())
api.register(UserProfileResource())
api.register(ExerciseResource())
api.register(CourseModuleResource())
api.register(SubmissionResource())
api.register(LearningObjectResource())

urlpatterns = patterns('',
    (r'^', include(api.urls)),
)
