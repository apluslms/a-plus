from django.urls import re_path

from . import views
from course.urls import INSTANCE_URL_PREFIX, MODULE_URL_PREFIX
from exercise.urls import EXERCISE_URL_PREFIX, SUBMISSION_URL_PREFIX

INSTANCE_URL_FILL = INSTANCE_URL_PREFIX[1:]
MODULE_URL_FILL = MODULE_URL_PREFIX[1:]
EXERCISE_URL_FILL = EXERCISE_URL_PREFIX[1:]
SUBMISSION_URL_FILL = SUBMISSION_URL_PREFIX[1:]

LTI_PREFIX = r'lti/'
LTI_SELECT_CONTENT_PREFIX = LTI_PREFIX + "select-content/"
LTI_INSTANCE_URL_PREFIX = LTI_PREFIX + INSTANCE_URL_FILL
LTI_EDIT_URL_PREFIX = LTI_INSTANCE_URL_PREFIX + r'teachers/'
LTI_USER_URL_PREFIX = LTI_INSTANCE_URL_PREFIX + r'user/'
LTI_MODULE_URL_PREFIX = LTI_PREFIX + MODULE_URL_FILL

LTI_EXERCISE_URL_PREFIX = LTI_PREFIX + EXERCISE_URL_FILL
LTI_SUBMISSION_URL_PREFIX = LTI_PREFIX + SUBMISSION_URL_FILL

urlpatterns = [
    re_path(LTI_PREFIX + r'login/$',
        views.lti_login),
    re_path(LTI_SELECT_CONTENT_PREFIX + '$',
        views.LtiSelectContentView.as_view(),
        name="lti-select-content"),
    re_path(LTI_SELECT_CONTENT_PREFIX + INSTANCE_URL_FILL +  '$',
        views.LtiSelectCourseView.as_view(),
        name="lti-select-course"),
    re_path(LTI_SELECT_CONTENT_PREFIX + MODULE_URL_FILL  + '$',
        views.LtiSelectModuleView.as_view(),
        name="lti-select-module"),
    re_path(LTI_SELECT_CONTENT_PREFIX + EXERCISE_URL_FILL + '$',
        views.LtiSelectExerciseView.as_view(),
        name="lti-select-exercise"),
    re_path(LTI_PREFIX + r'launch/$',
        views.LtiLaunchView.as_view(),
        name="lti-launch"),
    re_path(LTI_SUBMISSION_URL_PREFIX + r'$',
        views.LtiSubmissionView.as_view(),
        name="lti-submission"),
    re_path(LTI_EXERCISE_URL_PREFIX + r'$',
        views.LtiExerciseView.as_view(),
        name="lti-exercise"),
    re_path(LTI_MODULE_URL_PREFIX + r'$',
        views.LtiModuleView.as_view(),
        name="lti-module"),
    re_path(LTI_INSTANCE_URL_PREFIX + r'$',
        views.LtiInstanceView.as_view(),
        name="lti-course"),
]
