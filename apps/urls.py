from django.urls import re_path

from course.urls import INSTANCE_URL_PREFIX
from . import views

urlpatterns = [
    re_path(INSTANCE_URL_PREFIX + r'tabs/(?P<tab_id>\d+)/$',
    views.TabView.as_view(),
    name="apps-tab"),
]
