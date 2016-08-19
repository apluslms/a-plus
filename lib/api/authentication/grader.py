import logging
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from lib.crypto import get_valid_message
from lib.helpers import get_url_ip_address_list
from exercise.models import BaseExercise, Submission
from userprofile.models import GraderUser
from . import GRADER_AUTH_TOKEN


logger = logging.getLogger('aplus.authenticaion')


class GraderAuthentication(BaseAuthentication):
    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        token = request.GET.get(GRADER_AUTH_TOKEN, None)

        if token is None:
            return None

        # Get user by token. May raise AuthenticationFailed
        user = self.authenticate_credentials(token)

        # Make sure that remote address matches service address
        service_url = user._exercise.service_url
        ips = get_url_ip_address_list(service_url)
        ip = request.META["REMOTE_ADDR"]
        if ip not in ips:
            logger.error(
                "Request IP does not match exercise service URL: %s not in %s (%s)",
                ip,
                ips,
                service_url,
                extra={'request': request},
            )
            raise AuthenticationFailed(_("Client address doesn't match service address"))

        # All good
        return (user, token)

    def authenticate_credentials(self, token):
        """
        Resolve user from authentication token

        Args:
            token: authentication token in correct format

        Raises:
            AuthenticationFailed if authentication failed
        """
        token_type, token = token[0], token[1:]
        if token_type == 's':
            token_parts = token.split('.', 1)
            if len(token_parts) != 2:
                raise AuthenticationFailed(_("Authentication token isn't in correct format"))

            submission_id, submission_hash = token_parts
            try:
                submission = Submission.objects.get(id=submission_id, hash=submission_hash)
            except Submission.DoesNotExist:
                raise AuthenticationFailed(_("No valid submission for authenticaion token"))

            user = GraderUser.from_submission(submission)

        elif token_type == 'e':
            try:
                identifier = get_valid_message(token)
            except ValueError as e:
                raise AuthenticationFailed(_("Authentication token is corrupted: {}").format(e))

            identifier_parts = identifier.split('.', 1)
            if len(identifier_parts) != 2:
                raise AuthenticationFailed(_("Authentication token identifier isn't in correct format"))

            student_id, exercise_id = identifier_parts
            try:
                exercise = BaseExercise.objects.get(id=exercise_id)
            except BaseExercise.DoesNotExist:
                raise AuthenticationFailed(_("No valid exercise for authenticaion token"))

            user = GraderUser.from_exercise(exercise, student_id)

        else:
            raise AuthenticationFailed(_("Authentication token is invalid"))

        return user
