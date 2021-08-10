from django.http import UnreadablePostError
import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.http.request import HttpRequest

def skip_unreadable_post(record):
    """Skips log records of unfinished post requests."""
    return not record.exc_info or not issubclass(record.exc_info[0], UnreadablePostError)

class SecurityLog:
    """
    Static singleton class used for A+ - wide security logging.
    Django signals are used to track login/logout events.
    """

    seclogger = logging.getLogger('aplus.security')

    @staticmethod
    def logger() -> logging.Logger:
        return SecurityLog.seclogger

    @staticmethod
    def logevent(request: HttpRequest, type: str, message: str) -> None:
        # Unit tests do not have user defined in request object.
        if request and hasattr(request, 'user'):
            user=request.user
            ip=request.META.get('REMOTE_ADDR')
        else:
            user='?'
            ip='?'
        SecurityLog.logger().info("({}/{}): {}: {}".format(
            user,
            ip,
            type,
            message
        ))


# This example was used as an inspiration for the following functions:
# https://stackoverflow.com/questions/37618473/how-can-i-log-both-successful-and-failed-login-and-logout-attempts-in-django
@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    SecurityLog.logevent(request, "login", "")

@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    SecurityLog.logevent(request, "logout", "")

# Unfortunately the request object is not passed with this signal,
# so we cannot get the IP.
@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, **kwargs):
    SecurityLog.logevent(None, "login-failed","{credentials}".format(
        credentials=credentials)
    )
