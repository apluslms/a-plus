from django.conf.urls import patterns, url
from exercise.views import view_submission, view_exercise, \
    view_submitted_file, view_update_stats
from exercise.staff_views import list_exercise_submissions, \
    inspect_exercise_submission, add_or_edit_exercise, \
    fetch_exercise_metadata, assess_submission, resubmit_to_service, \
    create_and_assess_submission, add_deadline_rule_deviations, \
    list_deadline_rule_deviations, remove_deadline_rule_deviation, remove_exercise
from exercise.async_views import new_async_submission, grade_async_submission

urlpatterns = patterns('',
    (r'^(?P<exercise_id>\d+)/$', view_exercise),
    (r'^stats/(?P<exercise_id>\d+)/$', view_update_stats),
    (r'^submission/(?P<submission_id>\d+)/$', view_submission),
    (r'^submissions/list/(?P<exercise_id>\d+)/$', list_exercise_submissions),
    (r'^submissions/inspect/(?P<submission_id>\d+)/$',
     inspect_exercise_submission),
    (r'^submissions/assess/(?P<submission_id>\d+)/$', assess_submission),
    (r'^(?P<exercise_id>\d+)/create_and_assess_submission/$',
     create_and_assess_submission),
    (r'^submitted_file/(?P<submitted_file_id>\d+)/', view_submitted_file),
    (r'^manage/(?P<module_id>\d+)/$', add_or_edit_exercise),
    (r'^fetch_metadata/$', fetch_exercise_metadata),
    (r'^manage/(?P<module_id>\d+)/exercise_type/(?P<exercise_type>\w+)$',
     add_or_edit_exercise),
    (r'^manage/(?P<module_id>\d+)/(?P<exercise_id>\d+)/$',
     add_or_edit_exercise),
    (r'^remove/(?P<module_id>\d+)/(?P<exercise_id>\d+)/$',
     remove_exercise),
    (r'^rest/exercise/(?P<exercise_id>\d+)/students/(?P<student_ids>[\d\-]+)/(?'
     'P<hash>\w+)/$', new_async_submission),
    (r'^rest/submission/(?P<submission_id>\d+)/(?P<hash>\w+)/$',
     grade_async_submission),
    (r'^submissions/re-submit-to-service/(?P<submission_id>\d+)/$',
     resubmit_to_service),
    url(r'^deadline_rule_deviation/remove/(?P<deadline_rule_deviation_id>\d+)$',
        remove_deadline_rule_deviation, name="remove_dl_deviation"),
    url(r'^deadline_rule_deviation/(?P<course_instance>\d+)/add/$',
        add_deadline_rule_deviations, name="add_dl_deviations"),
    url(r'^deadline_rule_deviation/(?P<course_instance>\d+)/list/$',
        list_deadline_rule_deviations, name="list_dl_deviations"),
)
