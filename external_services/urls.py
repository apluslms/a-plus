from django.conf.urls import url

from course.urls import INSTANCE_URL_PREFIX
from . import views


urlpatterns = [
    url(INSTANCE_URL_PREFIX + r'lti-login/(?P<menu_id>\d+)/$',
    views.LTILoginView.as_view(),
    name="lti-login"),
]
