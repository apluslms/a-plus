from authorization.views import ResourceMixin
from django.core.exceptions import PermissionDenied
from django.template.response import SimpleTemplateResponse

from lib.viewbase import BaseMixin, BaseTemplateView
from authorization.permissions import ACCESS
from .models import UserProfile


class UserProfileMixin(ResourceMixin, BaseMixin):
    access_mode = ACCESS.STUDENT
    login_redirect = True

    def get_resource_objects(self):
        super().get_resource_objects()
        user = self.request.user
        if user.is_authenticated:
            self.profile = profile = user.userprofile
            self.is_external_student = profile.is_external
        else:
            self.profile = None
            self.is_external_student = False

        # Add available for template
        self.note("profile", "is_external_student")


class UserProfileView(UserProfileMixin, BaseTemplateView):
    pass
