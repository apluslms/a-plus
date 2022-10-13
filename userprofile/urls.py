from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
    url(r'^login/$', views.CustomLoginView.as_view(), name="login"),
    url(r'^logout/$', auth_views.LogoutView.as_view(template_name="userprofile/logout.html"),
        name="logout"),
    url(r'^privacy-notice/$', views.PrivacyNoticeView.as_view(),
        name="privacy_notice"),
    url(r'^accessibility-statement/$', views.AccessibilityStatementView.as_view(),
        name="accessibility_statement"),
    url(r'^support/$', views.SupportView.as_view(),
        name="support_channels"),
    url(r'^accounts/$', views.ProfileView.as_view(),
        name="profile"),
    url(r'^setlang', views.set_user_language, name="set-user-language"),
    url(r'^regentoken/$', views.regenerate_access_token, name="regenerate-access-token"),
    url(r'^teachers/$', views.TeacherListView.as_view(), name="teachers"),
]
