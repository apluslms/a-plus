from authorization.permissions import ACCESS
from lib.protocols import SupportsGetResourceObjects, SupportsNote
from lib.viewbase import BaseMixin, BaseTemplateView


class UserProfileMixin(BaseMixin, SupportsGetResourceObjects, SupportsNote):
    access_mode = ACCESS.STUDENT
    login_redirect = True

    def get_resource_objects(self) -> None:
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
