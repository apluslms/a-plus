import logging
from typing import List, Dict, Any, Tuple, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from aplus.api import api_reverse

import jwt
from jwcrypto import jwk
from oauthlib.openid import RequestValidator as OIDCRequestValidator
from oauthlib.common import Request as OAuthRequest
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from lib.helpers import build_aplus_url
from exercise.exercise_models import LTI1p3Exercise
from course.models import CourseInstance
from .models import LTI1p3Service


logger = logging.getLogger('aplus.external_services')

def _add_claim(id_token: dict, key: str, value: Any) -> None:
    id_token.update({f"https://purl.imsglobal.org/spec/lti/claim/{key}": value})


def prepare_lti1p3_initiate_login(
        service: LTI1p3Service,
        user: User,
        instance: CourseInstance,
        exercise: LTI1p3Exercise = None,
        ) -> List[Tuple[str, str]]:
    """
    Prepares LTI 1.3 initiate login request sent from A+ to LTI Tool, which is expected
    to respond by sending an Authentication request back. Returns parameters included in
    the request.
    """
    if user.is_anonymous:
        raise PermissionDenied()

    # LTI message hint is used to find course instance / exercise at later stages of handshake
    if exercise:
        hint = exercise.get_resource_link_id()
    else:
        hint = str(instance.pk)

    parameters = [
        ("iss", build_aplus_url('')),
        ("target_link_uri", service.url),
        ("login_hint", str(user.pk)),
        ("client_id", service.client_id),
        ("lti_deployment_id", service.deployment_id),
        ("lti_message_hint", hint),
    ]
    return parameters


class LTI1p3Client:
    """
    Represents a validated OAuth client (LTI 1.3 tool) interacting with A+ LTI platform.
    """
    def __init__(self, client_id):
        self.client_id = client_id


class LTI1p3AuthValidator(OIDCRequestValidator):
    """
    Implementation of oauthlib Auhtentication request validator for incoming OAuth2
    requests used in LTI 1.3.

    @param user: Django user associated with HTTP requests, when used in login
    authorization request triggered by A+ user.
    None, if request has originated from LTI tool.
    
    @param params: URL query parameters from OAuth request.
    """
    def __init__(self, user: User, params: dict, message_hint: Optional[str]):
        self.user = user
        self.redirect_uri = params.get('redirect_uri')
        self.login_hint = params.get('login_hint')
        self.instance = None
        self.exercise = None

        if not message_hint:
            raise OAuth2Error("Missing message_hint")

        hint = message_hint.split(':')
        try:
            self.instance = CourseInstance.objects.get(pk=int(hint[0]))
        except CourseInstance.DoesNotExist as e:
            raise OAuth2Error("Invalid message_hint: cannot find course instance") from e

        if len(hint) > 1:
            # When accessed from side menu, LTI request is not associated with exercise,
            # and then the exercise part of the hint is not defined.
            try:
                self.exercise = LTI1p3Exercise.objects.get(pk=int(hint[1]))
            except LTI1p3Exercise.DoesNotExist:
                pass

        client_id = params.get('client_id')
        if client_id:
            try:
                self.service = LTI1p3Service.objects.get(client_id=client_id)
            except LTI1p3Service.DoesNotExist as e:
                raise OAuth2Error("Invalid client ID") from e
        else:
            raise OAuth2Error("Client ID is not specified")

    def validate_client_id(self, client_id: str, request, *args, **kwargs) -> bool:
        if (self.service and self.service.client_id == client_id):
            return True

        logger.error("LTI 1.3: validate client failed for '%s'", client_id)
        return False

    def validate_redirect_uri(self, client_id: str, redirect_uri: str, request, *args, **kwargs) -> bool:
        # For now we do not have means for better validation, redirect_uri is not preconfigured.
        if redirect_uri:
            return True
        logger.error("LTI 1.3: validate redirect_uri failed for client '%s', uri: %s", client_id, redirect_uri)
        return False

    def validate_response_type(self, client_id: str, response_type: str, client, request, *args, **kwargs) -> bool:
        if (response_type == 'id_token'):
            return True

        logger.error("LTI 1.3: validate response_type failed for client '%s', type: %s", client_id, response_type)
        return False

    def validate_scopes(self,
            client_id: str,
            scopes: List[str],
            client: LTI1p3Client,
            request,
            *args,
            **kwargs,
            ) -> bool:
        # Auth login request, should always be 'openid'
        if scopes[0] != "openid":
            logger.error("LTI 1.3: Invalid scope for login request from '%s': %s", client_id, scopes[0])
            return False
        return True

    def validate_silent_authorization(self, request) -> bool:
        return True

    def validate_silent_login(self, request) -> bool:
        return True

    def validate_user_match(self, id_token_hint, scopes, claims, request) -> bool:
        if not (self.user and self.user.is_authenticated):
            logger.error("LTT 1.3: Received auth request, but there is no logged in user")
            return False
        if self.login_hint:
            if self.user.pk == int(self.login_hint):
                return True
            logger.error("LTI 1.3: A+ user does not match login hint, user: %d, login hint: %s",
                         self.user.pk,
                         self.login_hint)
            return False
        logger.error("LTI 1.3: Login hint is missing from auth request")
        return False

    def authenticate_client_id(self, client_id: str, request, *args, **kwargs) -> bool:
        # authenticate_client() checks that we have a valid preconfigured client.
        # We do not allow non-preconfigured clients.
        logger.info("LTI 1.3: not authenticating client ID: %s", client_id)
        return False

    def _set_custom_params(self, id_token: dict) -> None:
        if self.exercise:
            parsed = {}
            for param in self.exercise.custom.split():
                splitted = param.split('=')
                if (len(splitted) == 2):
                    parsed.update({splitted[0]: splitted[1]})
                else:
                    logger.warning("Invalid custom parameter in LTI config: %s", param)
            _add_claim(id_token, "custom", parsed)

    def _set_lti_roles(self, id_token: dict) -> None:
        roles = []
        if self.instance.is_teacher(self.user):
            roles.append("http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor")

        if self.instance.is_student(self.user):
            roles.append("http://purl.imsglobal.org/vocab/lis/v2/membership#Learner")

        if self.instance.is_assistant(self.user):
            roles.append("http://purl.imsglobal.org/vocab/lis/v2/membership/Instructor#TeachingAssistant")
        _add_claim(id_token, "roles", roles)

    def _set_launch_presentation(self, id_token: dict) -> None:
        param = { "locale": self.user.userprofile.language }
        if self.exercise and self.exercise.open_in_iframe:
            param.update({ "document_target": "iframe" })
        else:
            param.update({ "document_target": "window" })
        _add_claim(id_token, "launch_presentation", param)

    def _make_service_claim(self) -> dict:
        service = {
            "scope": [
                    "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly",
                    "https://purl.imsglobal.org/spec/lti-ags/scope/score",
                ],
            "lineitems": build_aplus_url(api_reverse(
                    'course-lineitems-list',
                    kwargs={ 'course_id' : str(self.instance.pk) },
            )),
        }
        if self.exercise:
            service.update({
                "lineitem": build_aplus_url(api_reverse(
                    'course-lineitems-detail',
                    kwargs={ 'course_id' : str(self.instance.pk), 'id' : str(self.exercise.pk) },
                ))
            })
        return service

    def finalize_id_token(self, id_token: dict, token: str, _token_handler, _request) -> str:
        # Resource link ID should be unique within the platform deployment
        # Build it based on course instance ID and exercise ID.
        # If exercise ID is not defined, the link is likely from the course menu.
        if self.exercise:
            link_id = self.exercise.get_resource_link_id()
        else:
            link_id = str(self.instance.pk)

        id_token.update({
            "iss": build_aplus_url(''),  # SERVICE_BASE_URL or BASE_URL
            "sub": str(self.user.pk),
            "exp": id_token["iat"] + settings.LTI_TOKEN_LIFETIME,
            "https://purl.imsglobal.org/spec/lti/claim/deployment_id": self.service.deployment_id,
            "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiResourceLinkRequest",
            "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
            "https://purl.imsglobal.org/spec/lti/claim/resource_link": {
                "id": link_id,
            },
            "https://purl.imsglobal.org/spec/lti/claim/target_link_uri": self.service.url,
            "https://purl.imsglobal.org/spec/lti/claim/context": {
                "id": link_id,
                "title": self.instance.course.name,
                "type": ["http://purl.imsglobal.org/vocab/lis/v2/course#CourseOffering"]
            },
            "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint": self._make_service_claim(),
        })

        if self.service.share_name:
            id_token.update({
                "email": self.user.email,
                "name": self.user.get_full_name(),
                "given_name": self.user.first_name,
                "family_name": self.user.last_name,
                "https://purl.imsglobal.org/spec/lti/claim/ext": {
                    "user_username": self.user.username,
                },
                "https://purl.imsglobal.org/spec/lti/claim/lis": {
                    "person_sourcedid": f"{self.user.userprofile.organization}:{self.user.userprofile.student_id}",
                },
            })

        self._set_lti_roles(id_token)
        self._set_custom_params(id_token)
        self._set_launch_presentation(id_token)
        logger.info("LTI 1.3: Finalizind ID Token: iss: %s; sub: %s", id_token['iss'], id_token['sub'])

        pem = settings.APLUS_AUTH_LOCAL['PRIVATE_KEY']
        key = jwk.JWK.from_pem(pem.encode("utf8"))
        kid = key.thumbprint()
        token = jwt.encode(id_token, pem, 'RS256', headers={'kid': kid})
        return token


class LTI1p3TokenValidator(OIDCRequestValidator):
    """
    Implementation of oauthlib token request validator for incoming OAuth2
    requests used in LTI 1.3.
    """
    def validate_grant_type(self,
            client_id,
            grant_type: str,
            client: LTI1p3Client,
            request,
            *args,
            **kwargs,
            ) -> bool:
        if client and grant_type == 'client_credentials':
            return True
        logger.error("LTI 1.3: validate_grant_type failed.")
        return False

    def authenticate_client(self, request: OAuthRequest, *args, **kwargs) -> bool:
        token = None
        for elem in request.decoded_body:
            if elem[0] == 'client_assertion':
                token = elem[1]
        if not token:
            logger.error("LTI 1.3: authenticate client failed: invalid token")
            return False

        # We need to do one pass without signature verification to find out client_id
        # and subsequent key details.
        decoded = jwt.decode(token, options={"verify_signature": False})
        sub = decoded['sub']
        iss = decoded['iss']
        request.client = LTI1p3Client(sub)
        try:
            service = LTI1p3Service.objects.get(client_id=sub)
        except LTI1p3Service.DoesNotExist:
            logger.error("LTI 1.3: Received JWT token for '%s' but such client ID does not exist.", sub)
            return False

        jwks_client = jwt.PyJWKClient(service.jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        token_url = build_aplus_url(reverse('external-services-token'))
        logger.info("LTI 1.3: authenticating client: %s", sub)
        try:
            _ = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=token_url,
                issuer=iss,
            )
        except (jwt.ExpiredSignatureError, jwt.InvalidAudienceError) as e:
            logger.error("LTI 1.3: JWT token decoding failed (%s): %s", sub, str(e))
            return False

        return True

    def validate_scopes(self,
            client_id: str,
            scopes: List[str],
            client: LTI1p3Client,
            request,
            *args,
            **kwargs,
            ) -> bool:
        for scope in scopes:
            # Token request, e.g. for submitting scores
            # Currently allowing scores from all registered services.
            # Should we have an option for not accepting scores from some tools?
            if scope not in [
                "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly",
                "https://purl.imsglobal.org/spec/lti-ags/scope/score",
            ]:
                logger.error("LTI 1.3: Invalid scope for token request from '%s': %s", client.client_id, scope)
                return False

        return True

    def save_bearer_token(self, token: Dict[str, str], request: OAuthRequest, *args, **kwargs) -> None:
        # We use JWT tokens, so there is no need to save anything to DB
        pass