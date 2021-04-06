import logging
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication
from django.conf import settings

from lib.crypto import get_valid_message
from lib.helpers import get_url_ip_address_list, get_remote_addr
from exercise.models import BaseExercise, Submission
from userprofile.models import GraderUser
from . import GRADER_AUTH_TOKEN

if settings.KUBERNETES_MODE:
    from kubernetes import client as k8s_client, config as k8s_config

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
        ip = get_remote_addr(request)

        if settings.KUBERNETES_MODE:
            # Check k8s pod IPs first (request from k8s cluster)
            auth_ok, error_str_k8s = self.authenticate_k8s(ip)
            if not auth_ok:
                # Otherwise, check service URL match (request from external sources)
                auth_ok, error_str_ext = self.authenticate_service(user, ip)
                if not auth_ok:
                    logger.error(error_str_k8s)
                    logger.error(error_str_ext)
                    raise AuthenticationFailed("Client address does not match service address or grader pod IP addresses.")
        else:
            auth_ok, error_str = self.authenticate_service(user, ip)
            if not auth_ok:
                logger.error(error_str)
                raise AuthenticationFailed("Client address does not match service address.")

        # All good
        return (user, token)

    def authenticate_k8s(self, ip):
        """
        Check if IP in grader pod IPs. Return tuple (auth_ok, error_str)
        """
        k8s_config.load_incluster_config()
        k8s_api = k8s_client.CoreV1Api()
        grader_pods = k8s_api.list_namespaced_pod(settings.KUBERNETES_NAMESPACE, label_selector="app=grader")
        grader_pod_ips = [pod.status.pod_ip for pod in grader_pods.items]

        if ip not in grader_pod_ips:
            err = "Request IP does not match grader pod IPs: {} not in {}".format(ip, grader_pod_ips)
            return (False, err)
        else:
            return (True, "")

    def authenticate_service(self, user, ip):
        """
        Check if request IP matches the exercise service URL. Return tuple (auth_ok, error_str)
        """
        # TODO: we do not know the language, but we expect that all versions of service_url are within the same domain
        service_url = user._exercise.as_leaf_class().get_service_url('en')
        ips = get_url_ip_address_list(service_url)
        if ip not in ips and ip != '127.0.0.1':
            err = "Request IP does not match exercise service URL: {} not in {} ({})".format(ip, ips, service_url)
            return (False, err)
        else:
            return (True, "")

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
