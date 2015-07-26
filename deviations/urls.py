from django.conf.urls import url

from course.urls import EDIT_URL_PREFIX
from . import teacher_views


urlpatterns = [
    url(EDIT_URL_PREFIX + r'deviations/$',
        teacher_views.ListDeadlinesView.as_view(),
        name="deviations-list-dl"),
    url(EDIT_URL_PREFIX + r'deviations/add/$',
        teacher_views.AddDeadlinesView.as_view(),
        name="deviations-add-dl"),
    url(EDIT_URL_PREFIX + r'deviations/(?P<deviation_id>\d+)/remove/$',
        teacher_views.RemoveDeadlineView.as_view(),
        name="deviations-remove-dl"),
]
