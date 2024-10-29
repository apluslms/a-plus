from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^login/$', views.AplusLoginView.as_view(), name="login"),
    re_path(r'^logout/$', views.AplusLogoutView.as_view(), name="logout"),
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
