from django.conf.urls import url

from course.urls import INSTANCE_URL_PREFIX
from . import views

urlpatterns = [
    url(INSTANCE_URL_PREFIX + r'tabs/(?P<tab_id>\d+)/$',
    views.TabView.as_view(),
    name="apps-tab"),
]
