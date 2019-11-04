from django.conf.urls import url

from course.urls import EDIT_URL_PREFIX
from . import views


urlpatterns = [
    url(EDIT_URL_PREFIX + r'deadline-deviations/$',
        views.ListDeadlinesView.as_view(),
        name="deviations-list-dl"),
    url(EDIT_URL_PREFIX + r'deadline-deviations/add/$',
        views.AddDeadlinesView.as_view(),
        name="deviations-add-dl"),
    url(EDIT_URL_PREFIX + r'deadline-deviations/override/$',
        views.OverrideDeadlinesView.as_view(),
        name="deviations-override-dl"),
    url(EDIT_URL_PREFIX + r'deadline-deviations/remove/$',
        views.RemoveManyDeadlinesView.as_view(),
        name="deviations-remove-many-dl"),
    url(EDIT_URL_PREFIX + r'deadline-deviations/(?P<deviation_id>\d+)/remove/$',
        views.RemoveDeadlineView.as_view(),
        name="deviations-remove-dl"),

    url(EDIT_URL_PREFIX + r'submission-deviations/$',
        views.ListSubmissionsView.as_view(),
        name="deviations-list-submissions"),
    url(EDIT_URL_PREFIX + r'submission-deviations/add/$',
        views.AddSubmissionsView.as_view(),
        name="deviations-add-submissions"),
    url(EDIT_URL_PREFIX + r'submission-deviations/override/$',
        views.OverrideSubmissionsView.as_view(),
        name="deviations-override-submissions"),
    url(EDIT_URL_PREFIX + r'submission-deviations/remove/$',
        views.RemoveManySubmissionsView.as_view(),
        name="deviations-remove-many-submissions"),
    url(EDIT_URL_PREFIX + r'submission-deviations/(?P<deviation_id>\d+)/remove/$',
        views.RemoveSubmissionView.as_view(),
        name="deviations-remove-submission"),
]
