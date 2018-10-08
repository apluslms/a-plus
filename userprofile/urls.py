from django.conf.urls import url, include
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
    url(r'^login/$', views.login,
        name="login"),
    url(r'^logout/$', auth_views.logout,
        { "template_name": "userprofile/logout.html" },
        name="logout"),
    url(r'^privacy-notice/$', views.PrivacyNoticeView.as_view(),
        name="privacy_notice"),
    url(r'^accounts/$', views.ProfileView.as_view(),
        name="profile"),
    url(r'^i18n/', include('django.conf.urls.i18n')),
]
