from datetime import datetime, timedelta
from typing import Any, Optional

from aplus_auth.auth.django import RemoteAuthenticator
from aplus_auth.payload import Payload
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from authorization.object_permissions import ObjectPermissions


class RemoteAuthenticationView(RemoteAuthenticator, APIView):
    """
    A view that signs a token for someone else after checking the permissions are ok.
    Default expiration time is 1 minute, and can be at most 1 day.

    Relevant payload fields:

    - exp: expiration time. If present, either a NumericDate integer, or a string
    in ISO calendar format (expire at) or HH:MM:SS format (expire in)
    - turl/taud: taud is the public key of the target service (with whom this token
    is supposed to be used), alternatively, one can give turl which is the target's
    alias or URL known by A+.
    - permissions: list of permissions to be included.
    See [AUTH.md](https://github.com/apluslms/a-plus/blob/master/doc/AUTH.md#permission-claims).
    For example, [["instance", 1, {"id": 5}]] where "5" is the id of the course instance.

    GET assumes the payload is sent as a part of a JWT token.

    POST allows you to specify the payload fields in the POST parameters.
    """
    permission_classes = [IsAuthenticated]

    def get_expiration_time(self, request: Request, payload: Payload):
        if payload.exp is not None:
            exp = payload.exp
            if isinstance(exp, datetime):
                exp = exp - datetime.now()
            return min(exp, timedelta(days=1))
        return self.expiration_time

    def get(self,
            request: Request,
            *,
            payload: Optional[Payload] = None,
            permissions: Optional[ObjectPermissions] = None,
            **kwargs: Any,
            ):
        if payload is None:
            payload = request.auth

        if not isinstance(payload, Payload):
            return Response("Missing payload", status=400)

        if permissions is None:
            if hasattr(request.user, "permissions"):
                permissions = request.user.permissions
            else:
                return Response("User is missing permissions attribute", status=500)

        if not isinstance(permissions, ObjectPermissions):
            return Response("Missing permissions", status=500)

        # If the object doesn't exist yet, the permissions are "ok" but it
        # might come to existence, in which case the signed token would
        # give access to it without the permissions necessarily being there.
        # This makes sure that the permission dicts cannot refer to some other
        # object that has not been created yet.
        payload.permissions = permissions.to_payload_permissions()

        try:
            return Response(self.get_token(request, payload), content_type="text/html")
        except ValueError as e:
            return Response(str(e), status=400)

    def post(self, request: Request, **kwargs: Any):
        payload = request.auth
        if not isinstance(payload, Payload):
            data = dict(request.data)
            try:
                payload = Payload(**data)
            except ValueError as e:
                return Response(str(e), status=400)
            payload.iss = f"user:{request.user.username}"
            try:
                # request.auth has already been authorized but the payload in
                # POST is not, so we need to check the permissions
                permissions = ObjectPermissions.from_payload(request.user, payload)
            except AuthenticationFailed as e:
                return Response(str(e), status=403)
        else:
            permissions = request.user.permissions

        return self.get(request, payload=payload, permissions=permissions, **kwargs)
