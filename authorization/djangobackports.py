from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.utils.encoding import force_text

class AccessMixin_1_10(object):
    """
    Backported version from Django 1.10
    """
    login_url = None
    permission_denied_message = ''
    raise_exception = False
    redirect_field_name = REDIRECT_FIELD_NAME
    def get_login_url(self):
        login_url = self.login_url or settings.LOGIN_URL
        return force_text(login_url)
    def get_permission_denied_message(self):
        return self.permission_denied_message
    def get_redirect_field_name(self):
        return self.redirect_field_name
    def handle_no_permission(self):
        if self.raise_exception:
            raise PermissionDenied(self.get_permission_denied_message())
        return redirect_to_login(self.request.get_full_path(),
                                    self.get_login_url(),
                                    self.get_redirect_field_name())