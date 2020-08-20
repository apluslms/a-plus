from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
import jwt

class WebToken:
    @classmethod
    def from_jwt(cls, token, secret= None):
        if not secret:
            secret = settings.SECRET_KEY
        payload = jwt.decode(token, secret)
        return cls(payload)

    def __init__(self, payload={}):
        self._payload = payload
        self.user_id = payload.get('uid')
        self.course_id = payload.get('course')

    def verify_user(self, user):
        return self.user_id == user.id

class CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        # Return the failure reason instead of an HttpResponse
        return reason

class SessionAuthentication:
    """
    Use Django's session framework for authentication.
    """

    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """
        # Get the session-based user from the underlying HttpRequest object
        user = getattr(request._request, 'user', None)

        # Unauthenticated, CSRF validation not required
        if not user or not user.is_active:
            return None

        self.enforce_csrf(request)
        
        if 'Authorization' in request.headers:
            try:
                scheme, token = request.headers['Authorization'].split()
                if scheme != 'Bearer':
                    raise ValueError
                web_token = WebToken.from_jwt(token)
            except (ValueError, jwt.exceptions.InvalidSignatureError, jwt.exceptions.DecodeError):
                return (user, None)
            if web_token.verify_user(user):
                return (user, web_token)
        
        # CSRF passed with authenticated user
        return (user, None)

    def enforce_csrf(self, request):
        """
        Enforce CSRF validation for session based authentication.
        """
        check = CSRFCheck()
        # populates request.META['CSRF_COOKIE'], which is used in process_view()
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            # CSRF failed, bail with explicit error message
            raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)