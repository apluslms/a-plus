from typing import Optional

from aplus_auth.auth.django import RemoteAuthenticator
from aplus_auth.exceptions import AuthenticationFailed
from aplus_auth.payload import Payload
from django.http import HttpRequest
from rest_framework.views import APIView

from lib.api.authentication.grader import GraderAuthentication
from lib.aplus_auth import url_to_audience


class RemoteAuthenticationView(RemoteAuthenticator, APIView):
    """A view that signs a token for someone else after checking the permissions are ok"""

    def has_permission(self, request: HttpRequest, payload: Payload) -> Optional[str]:
        try:
            user_token = GraderAuthentication().authenticate_payload(request, payload)
        except AuthenticationFailed as e:
            return str(e)
        if user_token is None:
            return "User not found"
        else:
            return None

    def get_audience(self, alias: str) -> str:
        return url_to_audience(alias)
