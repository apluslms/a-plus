from django.conf.urls.defaults import *
from tastypie.api import Api
from course.api import CourseResource, CourseInstanceResource
from userprofile.api import UserProfileResource
from course.api import CourseInstanceSummaryResource
from exercise.api import ExerciseResource, CourseModuleResource, \
  SubmissionResource, SubmissionContentResource, LearningObjectResource

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
    (r'^', include(api.urls)),
)
