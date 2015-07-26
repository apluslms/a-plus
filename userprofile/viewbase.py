from django.views.generic.base import View

from lib.viewbase import BaseMixin, BaseTemplateView
from .models import UserProfile


# A class in later Django versions.
try:
    from django.contrib.auth.mixins import AccessMixin
except ImportError:
    from django.conf import settings
    from django.contrib.auth.views import redirect_to_login
    from django.contrib.auth import REDIRECT_FIELD_NAME
    class AccessMixin(object):
        def handle_no_permission(self):
            return redirect_to_login(
                self.request.get_full_path(),
                settings.LOGIN_URL,
                REDIRECT_FIELD_NAME
            )


class ACCESS(object):
    ANONYMOUS = 0
    STUDENT = 1
    ASSISTANT = 5
    GRADING = 6
    TEACHER = 10


class LoginException(Exception):
    pass


class UserProfileMixin(BaseMixin, AccessMixin):
    access_mode = ACCESS.STUDENT

    def get_resource_objects(self):
        super().get_resource_objects()
        if self.request.user.is_authenticated():
            self.profile = UserProfile.get_by_request(self.request)
        else:
            self.profile = None
        self.note("profile")

    def access_control(self):
        super().access_control()
        if self.access_mode > ACCESS.ANONYMOUS \
                and not self.request.user.is_authenticated():
            raise LoginException()

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except LoginException:
            return self.handle_no_permission()


class UserProfileView(UserProfileMixin, BaseTemplateView):
    pass
