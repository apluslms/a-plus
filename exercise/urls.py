from django.urls import re_path

from course.urls import INSTANCE_URL_PREFIX, MODULE_URL_PREFIX, \
    USER_URL_PREFIX, EDIT_URL_PREFIX
from . import views, staff_views


EXERCISE_URL_PREFIX = MODULE_URL_PREFIX \
    + r'(?P<exercise_path>[\w\d\-\.\/]+)/'
SUBMISSION_URL_PREFIX = EXERCISE_URL_PREFIX \
    + r'submissions/(?P<submission_id>\d+)/'

urlpatterns = [

    # In the ordering, note that most general exercise URL has to be last.

    re_path(INSTANCE_URL_PREFIX + r'toc/$',
        views.TableOfContentsView.as_view(),
        name="toc"),
    re_path(USER_URL_PREFIX + r'results/$',
        views.ResultsView.as_view(),
        name="results"),
    re_path(SUBMISSION_URL_PREFIX + r'$',
        views.SubmissionView.as_view(),
        name="submission"),
    re_path(SUBMISSION_URL_PREFIX + r'plain/$',
        views.SubmissionPlainView.as_view(),
        name="submission-plain"),
    re_path(SUBMISSION_URL_PREFIX + r'poll/$',
        views.SubmissionPollView.as_view(),
        name="submission-poll"),
    re_path(SUBMISSION_URL_PREFIX \
            + r'file/(?P<file_id>\d+)/(?P<file_name>[\w\d\_\-\.]+)',
        views.SubmittedFileView.as_view(),
        name="submission-file"),

    re_path(SUBMISSION_URL_PREFIX \
            + r'add-taggings/(?P<subtag_id>\d+)$',
            views.SubmissionTaggingAddView.as_view(),
            name="add-tag-to-submissions"),
    re_path(SUBMISSION_URL_PREFIX \
            + r'remove-taggings/(?P<subtag_id>\d+)$',
            views.SubmissionTaggingRemoveView.as_view(),
            name="remove-tag-from-submissions"),

    re_path(EXERCISE_URL_PREFIX + r'submissions/$',
        staff_views.ListSubmissionsView.as_view(),
        name="submission-list"),
    re_path(EXERCISE_URL_PREFIX + r'submissions/regrade/$',
        staff_views.StartRegradeView.as_view(),
        name="submission-mass-regrade"),
    re_path(EXERCISE_URL_PREFIX + r'submissions/summary/$',
        staff_views.SubmissionsSummaryView.as_view(),
        name="submission-summary"),
    re_path(EXERCISE_URL_PREFIX + r'submissions/create_and_assess/$',
        staff_views.CreateSubmissionView.as_view(),
        name="submission-create"),
    re_path(EXERCISE_URL_PREFIX + r'submitters/$',
        staff_views.ListSubmittersView.as_view(),
        name="submitter-list"),
    re_path(EXERCISE_URL_PREFIX + r'submitters/(?P<user_id>\d+)/$',
        staff_views.InspectSubmitterView.as_view(),
        name="submitter-inspect"),
    re_path(EXERCISE_URL_PREFIX + r'submitters/next-unassessed/$',
        staff_views.NextUnassessedSubmitterView.as_view(),
        name="submission-next-unassessed"),
    re_path(SUBMISSION_URL_PREFIX + r'approve/$',
        staff_views.SubmissionApprovalView.as_view(),
        name="submission-approve"),
    re_path(SUBMISSION_URL_PREFIX + r'inspect/$',
        staff_views.InspectSubmissionView.as_view(),
        name="submission-inspect"),
    re_path(SUBMISSION_URL_PREFIX + r're-submit/$',
        staff_views.ResubmitSubmissionView.as_view(),
        name="submission-re-submit"),
    re_path(SUBMISSION_URL_PREFIX + r'increase-max/$',
        staff_views.IncreaseSubmissionMaxView.as_view(),
        name="submission-increase-max"),
    re_path(SUBMISSION_URL_PREFIX + r'edit-submitters/$',
        staff_views.EditSubmittersView.as_view(),
        name="submission-edit-submitters"),
    re_path(EDIT_URL_PREFIX + r'results/$',
        staff_views.AllResultsView.as_view(),
        name="all-results"),

    re_path(MODULE_URL_PREFIX + r'save_points_goal_form/$',
        views.StudentModuleGoalFormView.as_view(),
        name="save_points_goal_form_view"),
    re_path(MODULE_URL_PREFIX + r'delete_points_goal_form/$',
        views.StudentModuleGoalFormView.as_view(),
        name="delete_points_goal_form_view"),

    re_path(EDIT_URL_PREFIX + r'analytics/$',
        staff_views.AnalyticsView.as_view(),
        name="analytics"),
    re_path(EDIT_URL_PREFIX + r'participants/(?P<user_id>[\d]+)$',
        staff_views.UserResultsView.as_view(),
        name="user-results"),
    re_path(EDIT_URL_PREFIX + r'fetch-metadata/$',
        staff_views.FetchMetadataView.as_view(),
        name="exercise-metadata"),
    re_path(EDIT_URL_PREFIX + r'approve/module/$',
        staff_views.SubmissionApprovalByModuleView.as_view(),
        name="submission-approve-module"),
    re_path(EXERCISE_URL_PREFIX + r'plain/$',
        views.ExercisePlainView.as_view(),
        name="exercise-plain"),
    re_path(EXERCISE_URL_PREFIX + r'info/model/$',
        views.ExerciseModelView.as_view(),
        name="exercise-model"),
    re_path(EXERCISE_URL_PREFIX + r'info/template/$',
        views.ExerciseTemplateView.as_view(),
        name="exercise-template"),
    re_path(EXERCISE_URL_PREFIX + r'info/$',
        views.ExerciseInfoView.as_view(),
        name="exercise-info"),
    re_path(EXERCISE_URL_PREFIX + r'draft/$',
        views.SubmissionDraftView.as_view(),
        name="submission-draft"),
    re_path(EXERCISE_URL_PREFIX + r'$',
        views.ExerciseView.as_view(),
        name="exercise"),
]
