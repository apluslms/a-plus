import logging
from typing import Any, Dict, List, Optional, Tuple

from aplus_auth import settings as auth_settings
from aplus_auth.payload import Payload, Permission
from aplus_auth.auth import get_token_from_headers
from aplus_auth.auth.django import ServiceAuthentication
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from authorization.object_permissions import ObjectPermissions
from lib.crypto import get_valid_message
from exercise.models import BaseExercise, Submission
from userprofile.models import GraderUser
from . import GRADER_AUTH_TOKEN


logger = logging.getLogger('aplus.authentication')


class GraderAuthentication(ServiceAuthentication[GraderUser], BaseAuthentication):
    allow_any_issuer = True

    def get_token(self, request: Request) -> Optional[str]:
        token = get_token_from_headers(request.headers)
        if token is not None:
            return token

        return None

    def authenticate(self, request: Request) -> Optional[Tuple[GraderUser, Payload]]:
        if self.get_token(request):
            return super().authenticate(request)
        else:
            token = request.GET.get(GRADER_AUTH_TOKEN, None)
            if token is None:
                return None

            permissions = ObjectPermissions()
            payload = Payload()
            self.add_token_permissions(token, permissions, payload)
            return GraderUser(token, permissions), payload

    def add_token_permissions(self, token: str, permissions: ObjectPermissions, payload: Payload):
        if token[0] == "s":
            submission = self.authenticate_submission_token(token[1:])
            payload.permissions.submissions.add(Permission.WRITE, id=submission.id)
            exercise = submission.exercise
        elif token[0] == "e":
            exercise, user_id = self.authenticate_exercise_token(token[1:])
            perm_dict: Dict[str, Any] = {"exercise_id": exercise.id, "user_id": user_id}
            payload.permissions.submissions.add(Permission.CREATE, **perm_dict)
        else:
            raise AuthenticationFailed("Authentication token is invalid.")

        payload.permissions.courses.add(Permission.WRITE, id=exercise.course_instance.course.id)

    def get_user(self, request: Request, id: str, payload: Payload) -> GraderUser:
        # check public key is allowed access
        if auth_settings().DISABLE_LOGIN_CHECKS:
            if not settings.DEBUG:
                logger.warn("!!! JWT login checks are disabled !!!")
        elif id not in settings.ALIAS_TO_PUBLIC_KEY.values():
            logger.info(f"Service not authorized: {id}")
            raise AuthenticationFailed("ID not trusted")

        permissions = ObjectPermissions.from_payload(payload)

        tokens: List[str] = payload.get("tokens", []) # type: ignore
        atoken = request.GET.get(GRADER_AUTH_TOKEN, None)
        if atoken is not None:
            tokens.append(atoken)

        for token in tokens:
            self.add_token_permissions(token, permissions, payload)

        return GraderUser(id, permissions)

    def authenticate_submission_token(self, submission_token) -> Submission:
        """
        Resolve submission from authentication token

        Args:
            submission_token: authentication token in correct format

        Raises:
            AuthenticationFailed if authentication failed
        """
        token_parts = submission_token.split('.', 1)
        if len(token_parts) != 2:
            raise AuthenticationFailed("Submission token isn't in correct format.")

        submission_id, submission_hash = token_parts
        try:
            submission_id = int(submission_id, 16)
        except ValueError:
            raise AuthenticationFailed("Submission token isn't in correct format.")

        try:
            submission = Submission.objects.get(id=submission_id, hash=submission_hash)
        except Submission.DoesNotExist:
            raise AuthenticationFailed("No valid submission for submission token.")

        return submission

    def authenticate_exercise_token(self, exercise_token) -> Tuple[BaseExercise, str]:
        """
        Resolve exercise from authentication token

        Args:
            exercise_token: authentication token in correct format

        Raises:
            AuthenticationFailed if authentication failed
        """
        try:
            identifier = get_valid_message(exercise_token)
        except ValueError as e:
            raise AuthenticationFailed("Exercise token is corrupted '{error!s}'.".format(error=e))

        identifier_parts = identifier.split('.', 1)
        if len(identifier_parts) != 2:
            raise AuthenticationFailed("Exercise token identifier "
                                        "isn't in correct format.")

        user_id, exercise_id = identifier_parts
        try:
            exercise = BaseExercise.objects.get(id=exercise_id)
        except BaseExercise.DoesNotExist:
            raise AuthenticationFailed("No valid exercise for exercise token.")

        return exercise, user_id
