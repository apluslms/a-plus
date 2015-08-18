from django.conf.urls import url

from course.urls import USER_URL_PREFIX
from . import views


urlpatterns = [
    url(USER_URL_PREFIX + r'notifications/$',
        views.NotificationsView.as_view(),
        name="notifications"),
]
