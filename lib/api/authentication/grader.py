import logging
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from lib.crypto import get_valid_message
from lib.helpers import get_url_ip_address_list, get_remote_addr
from exercise.models import BaseExercise, Submission
from userprofile.models import GraderUser
from . import GRADER_AUTH_TOKEN


logger = logging.getLogger('aplus.authentication')


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
        ip = get_remote_addr(request)
        if ip not in ips and ip != '127.0.0.1':
            logger.error(
                "Request IP does not match exercise service URL: %s not in %s (%s)",
                ip,
                ips,
                service_url,
            )
            raise AuthenticationFailed("Client address does not match service address.")

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
                raise AuthenticationFailed("Authentication token isn't in correct format.")

            submission_id, submission_hash = token_parts
            try:
                submission_id = int(submission_id, 16)
            except ValueError:
                raise AuthenticationFailed("Authentication token isn't in correct format.")

            try:
                submission = Submission.objects.get(id=submission_id, hash=submission_hash)
            except Submission.DoesNotExist:
                raise AuthenticationFailed("No valid submission for authentication token.")

            user = GraderUser.from_submission(submission)

        elif token_type == 'e':
            try:
                identifier = get_valid_message(token)
            except ValueError as e:
                raise AuthenticationFailed("Authentication token is corrupted '{error!s}'.".format(error=e))

            identifier_parts = identifier.split('.', 1)
            if len(identifier_parts) != 2:
                raise AuthenticationFailed("Authentication token identifier "
                                           "isn't in correct format.")

            student_id, exercise_id = identifier_parts
            try:
                exercise = BaseExercise.objects.get(id=exercise_id)
            except BaseExercise.DoesNotExist:
                raise AuthenticationFailed("No valid exercise for authentication token.")

            user = GraderUser.from_exercise(exercise, student_id)

        else:
            raise AuthenticationFailed("Authentication token is invalid.")

        return user
