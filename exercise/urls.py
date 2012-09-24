from django.conf.urls.defaults import *
from exercise.views import view_submission, view_exercise, view_submitted_file
from exercise.staff_views import list_exercise_submissions, inspect_exercise_submission, \
    add_or_edit_exercise, fetch_exercise_metadata, submission_assessment
from exercise.async_views import new_async_submission, grade_async_submission

urlpatterns = patterns('',
    (r'^(?P<exercise_id>\d+)/$', view_exercise),
    (r'^submission/(?P<submission_id>\d+)/$', view_submission),
    (r'^submissions/list/(?P<exercise_id>\d+)/$', list_exercise_submissions),
    (r'^submissions/inspect/(?P<submission_id>\d+)/$', inspect_exercise_submission),
    (r'^submissions/assess/(?P<submission_id>\d+)/$', submission_assessment),
    (r'^submitted_file/(?P<submitted_file_id>\d+)/', view_submitted_file),
    (r'^manage/(?P<module_id>\d+)/$', add_or_edit_exercise),
    (r'^fetch_metadata/$', fetch_exercise_metadata),
    (r'^manage/(?P<module_id>\d+)/(?P<exercise_id>\d+)/$', add_or_edit_exercise),
    (r'^rest/exercise/(?P<exercise_id>\d+)/students/(?P<student_ids>[\d\-]+)/(?P<hash>\w+)/$', new_async_submission),
    (r'^rest/submission/(?P<submission_id>\d+)/(?P<hash>\w+)/$', grade_async_submission),
)