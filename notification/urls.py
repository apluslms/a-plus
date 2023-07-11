from django.urls import re_path

from course.urls import USER_URL_PREFIX
from . import views


urlpatterns = [
    re_path(USER_URL_PREFIX + r'notify/(?P<notification_id>\d+)/$',
        views.NotificationRedirectView.as_view(),
        name="notify"),
]
