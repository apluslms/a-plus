from django.conf.urls import url

from course.urls import USER_URL_PREFIX
from . import views


urlpatterns = [
    url(USER_URL_PREFIX + r'notify/(?P<notification_id>\d+)/$',
        views.NotificationRedirectView.as_view(),
        name="notify"),
]
