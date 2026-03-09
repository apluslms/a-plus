from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [
    path('login/', views.AplusLoginView.as_view(), name="login"),
    path('logout/', views.AplusLogoutView.as_view(), name="logout"),
    path('privacy-notice/', views.PrivacyNoticeView.as_view(),
        name="privacy_notice"),
    path('cookie-notice/', views.CookieNoticeView.as_view(),
        name="cookie_notice"),
    path('accessibility-statement/', views.AccessibilityStatementView.as_view(),
        name="accessibility_statement"),
    path('support/', views.SupportView.as_view(),
        name="support_channels"),
    path('accounts/', views.ProfileView.as_view(),
        name="profile"),
    re_path(r'^setlang', views.set_user_language,
        name="set-user-language"),
    path('regentoken/', views.regenerate_access_token,
        name="regenerate-access-token"),
    path('teachers/', views.TeacherListView.as_view(),
        name="teachers"),
    path('pseudonymize/', views.PseudonymizeView.as_view(),
        name="toggle-pseudonymization"),
]
