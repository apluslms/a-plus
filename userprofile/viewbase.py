from django.core.exceptions import PermissionDenied
from django.template.response import SimpleTemplateResponse
from django.views.generic.base import View

from lib.viewbase import BaseMixin, BaseTemplateView
from .models import UserProfile


class ACCESS(object):
    ANONYMOUS = 0
    ENROLL = 1
    STUDENT = 3
    ENROLLED = 4
    ASSISTANT = 5
    GRADING = 6
    TEACHER = 10


class UserProfileMixin(BaseMixin):
    access_mode = ACCESS.STUDENT
    login_redirect = True

    def get_resource_objects(self):
        super().get_resource_objects()
        user = self.request.user
        if user.is_authenticated():
            self.profile = profile = user.userprofile
            self.is_external_student = profile.is_external
        else:
            self.profile = None
            self.is_external_student = False

        # Add available for template
        self.note("profile", "is_external_student")

    def access_control(self):
        super().access_control()
        if self.access_mode > ACCESS.ANONYMOUS \
                and not self.request.user.is_authenticated():
            raise PermissionDenied


class UserProfileView(UserProfileMixin, BaseTemplateView):
    pass
