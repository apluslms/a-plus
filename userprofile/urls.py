from django.urls import re_path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
    re_path(r'^login/$', views.CustomLoginView.as_view(), name="login"),
    re_path(r'^logout/$', auth_views.LogoutView.as_view(template_name="userprofile/logout.html"),
        name="logout"),
    re_path(r'^privacy-notice/$', views.PrivacyNoticeView.as_view(),
        name="privacy_notice"),
    re_path(r'^accessibility-statement/$', views.AccessibilityStatementView.as_view(),
        name="accessibility_statement"),
    re_path(r'^support/$', views.SupportView.as_view(),
        name="support_channels"),
    re_path(r'^accounts/$', views.ProfileView.as_view(),
        name="profile"),
    re_path(r'^setlang', views.set_user_language,
        name="set-user-language"),
    re_path(r'^regentoken/$', views.regenerate_access_token,
        name="regenerate-access-token"),
    re_path(r'^teachers/$', views.TeacherListView.as_view(),
        name="teachers"),
    re_path(r'^pseudonymize/$', views.PseudonymizeView.as_view(),
        name="toggle-pseudonymization"),
]
