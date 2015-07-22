from django.conf.urls import url

from course.urls import EDIT_URL_PREFIX
from . import teacher_views


urlpatterns = [
    url(EDIT_URL_PREFIX + r'deviations/$',
        teacher_views.list_dl, name="deviations-list-dl"),
    url(EDIT_URL_PREFIX + r'deviations/add/$',
        teacher_views.add_dl, name="deviations-add-dl"),
    url(EDIT_URL_PREFIX + r'deviations/(?P<deviation_id>\d+)/remove/$',
        teacher_views.remove_dl, name="deviations-remove-dl"),
]
