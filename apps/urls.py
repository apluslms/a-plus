from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'tab/(?P<tab_id>\d+)/$', views.view_tab, name="apps-tab"),
]
