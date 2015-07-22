from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'groups/$', views.view_groups, name="groups"),
]
