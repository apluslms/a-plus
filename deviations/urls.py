from django.conf.urls import url

from course.urls import EDIT_URL_PREFIX
from . import views


urlpatterns = [
    url(EDIT_URL_PREFIX + r'deviations/$',
        views.ListDeadlinesView.as_view(),
        name="deviations-list-dl"),
    url(EDIT_URL_PREFIX + r'deviations/add/$',
        views.AddDeadlinesView.as_view(),
        name="deviations-add-dl"),
    url(EDIT_URL_PREFIX + r'deviations/(?P<deviation_id>\d+)/remove/$',
        views.RemoveDeadlineView.as_view(),
        name="deviations-remove-dl"),
]
