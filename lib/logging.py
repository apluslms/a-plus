from django.http import UnreadablePostError
import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.http.request import HttpRequest
from format_cef import format_cef
from aplus import VERSION


CEF_VENDOR = 'Aalto'
CEF_PRODUCT = 'aplus'

def skip_unreadable_post(record):
    """Skips log records of unfinished post requests."""
    return not record.exc_info or not issubclass(record.exc_info[0], UnreadablePostError)

class SecurityLog:
    """
    Static singleton class used for A+ - wide security logging,
    to produce ArcSight Common Event Format (CEF) log.
    Django signals are used to track login/logout events.
    """

    seclogger = logging.getLogger('aplus.security')

    @staticmethod
    def logger() -> logging.Logger:
        return SecurityLog.seclogger

    @staticmethod
    def logevent(
            request: HttpRequest,
            type: str, # pylint: disable=redefined-builtin
            message: str,
            severity: int = 5,
            ) -> None:
        extensions = {}
        # Unit tests may not have user or source address defined.
        if request:
            if hasattr(request, 'user'):
                extensions['sourceUserName'] = str(request.user)
                extensions['sourceUserId'] = str(request.user.id)
            if (addr := request.META.get('REMOTE_ADDR')):
                extensions['sourceAddress'] = addr

        SecurityLog.logger().info(
            format_cef(
                CEF_VENDOR,
                CEF_PRODUCT,
                VERSION,
                type,
                message,
                severity,
                extensions,
            ).decode("utf-8")
        )


# This example was used as an inspiration for the following functions:
# https://stackoverflow.com/questions/37618473/how-can-i-log-both-successful-and-failed-login-and-logout-attempts-in-django
@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs): # pylint: disable=unused-argument
    SecurityLog.logevent(request, "login", "")

@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs): # pylint: disable=unused-argument
    SecurityLog.logevent(request, "logout", "")

# Unfortunately the request object is not passed with this signal,
# so we cannot get the IP.
@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, **kwargs): # pylint: disable=unused-argument
    try:
        SecurityLog.logevent(None, "login-failed", f"username: {credentials['username']}")
    except KeyError:
        # Unit tests do not have 'username' in credentials, let's not fail them for that
        pass
