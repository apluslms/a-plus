from django.urls import re_path

from course.urls import EDIT_URL_PREFIX
from . import views


urlpatterns = [
    re_path(EDIT_URL_PREFIX + r'deadline-deviations/$',
        views.ListDeadlinesView.as_view(),
        name="deviations-list-dl"),
    re_path(EDIT_URL_PREFIX + r'deadline-deviations/add/$',
        views.AddDeadlinesView.as_view(),
        name="deviations-add-dl"),
    re_path(EDIT_URL_PREFIX + r'deadline-deviations/override/$',
        views.OverrideDeadlinesView.as_view(),
        name="deviations-override-dl"),
    re_path(EDIT_URL_PREFIX + r'deadline-deviations/remove/$',
        views.RemoveDeadlinesView.as_view(),
        name="deviations-remove-dl"),
    re_path(EDIT_URL_PREFIX + r'deadline-deviations/remove-id/$',
        views.RemoveDeadlinesByIDView.as_view(),
        name="deviations-remove-dl-id"),

    re_path(EDIT_URL_PREFIX + r'submission-deviations/$',
        views.ListSubmissionsView.as_view(),
        name="deviations-list-submissions"),
    re_path(EDIT_URL_PREFIX + r'submission-deviations/add/$',
        views.AddSubmissionsView.as_view(),
        name="deviations-add-submissions"),
    re_path(EDIT_URL_PREFIX + r'submission-deviations/override/$',
        views.OverrideSubmissionsView.as_view(),
        name="deviations-override-submissions"),
    re_path(EDIT_URL_PREFIX + r'submission-deviations/remove/$',
        views.RemoveSubmissionsView.as_view(),
        name="deviations-remove-submissions"),
    re_path(EDIT_URL_PREFIX + r'submission-deviations/remove-id/$',
        views.RemoveSubmissionsByIDView.as_view(),
        name="deviations-remove-submissions-id"),
]
