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
        views.RemoveDeadlinesView.as_view(),
        name="deviations-remove-dl"),
    url(EDIT_URL_PREFIX + r'deadline-deviations/remove-id/$',
        views.RemoveDeadlinesByIDView.as_view(),
        name="deviations-remove-dl-id"),

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
        views.RemoveSubmissionsView.as_view(),
        name="deviations-remove-submissions"),
    url(EDIT_URL_PREFIX + r'submission-deviations/remove-id/$',
        views.RemoveSubmissionsByIDView.as_view(),
        name="deviations-remove-submissions-id"),
]
