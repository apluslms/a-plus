import datetime
import logging

import oauthlib.oauth1.rfc5849
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from external_services.models import LTIService
from .oauth_nonce_cache import OAuthNonceCache
from .parsers import parse_sourced_id
from userprofile.models import LTIServiceUser


logger = logging.getLogger('aplus.external_services.api')


def verify_oauth_body_hash_and_signature(request, req_body_hash, lti_exercise=None): # pylint: disable=too-many-locals
    '''
    Verify that the request has valid OAuth 1.0 signature and body hash.
    @param request Django HttpRequest
    @param req_body_hash base64-encoded SHA-1 hash of the request body (string)
    @param lti_exercise the instance of the LTIExercise is used to verify that
    the LTI service set for the exercise matches the oauth_consumer_key parameter
    of the request.
    @return tuple (boolean, error_message) boolean is True if verification succeeded,
    False otherwise.
    '''
    headers = {
        'Content-Type': request.content_type,
        'Authorization': request.META.get('HTTP_AUTHORIZATION'),
        'Host': request.META.get('HTTP_HOST'),
    }
    # all OAuth parameters must be given in the HTTP Authorization header
    # (not in POST data or GET query parameters) when a body hash is used
    # to secure the request body
    all_req_oauth_params = oauthlib.oauth1.rfc5849.signature.collect_parameters(
        headers=headers, exclude_oauth_signature=False)
    # collect_parameters returns a list of key-value pairs
    req_oauth_params_dict = dict(all_req_oauth_params)

    # check oauth_consumer_key and find the corresponding secret
    consumer_key = req_oauth_params_dict.get('oauth_consumer_key')
    if not consumer_key:
        return False, 'oauth_consumer_key missing'
    try:
        lti_service = LTIService.objects.get(consumer_key=consumer_key)
    except (LTIService.DoesNotExist, LTIService.MultipleObjectsReturned):
        return False, 'unknown oauth_consumer_key'

    if lti_exercise and lti_exercise.lti_service.pk != lti_service.pk:
        # the consumer key refers to a different LTI service than the exercise
        return False, 'oauth_consumer_key mismatch'
    client_secret = lti_service.consumer_secret

    # check the OAuth timestamp. Do not allow old requests in order to prevent replay attacks.
    try:
        timestamp = datetime.datetime.utcfromtimestamp(int(req_oauth_params_dict.get('oauth_timestamp')))
        # oauth_timestamp: seconds since January 1, 1970 00:00:00 GMT
    except ValueError:
        return False, 'oauth_timestamp is missing or has an invalid format'

    now = datetime.datetime.utcnow()
    delta = datetime.timedelta(seconds=OAuthNonceCache.CACHE_TIMEOUT_SECONDS)
    if not (now - delta < timestamp and timestamp < now + delta): # pylint: disable=chained-comparison
        return False, 'oauth_timestamp has expired'

    # check OAuth nonce: The nonce value MUST be unique across all requests with
    # the same timestamp, client credentials, and token combinations.
    # Previously seen nonces are kept in the cache for a few minutes
    # (the duration must match the accepted timestamp age).
    nonce = req_oauth_params_dict.get('oauth_nonce')
    if not nonce:
        return False, 'oauth_nonce missing'
    nonce_cache = OAuthNonceCache(nonce, req_oauth_params_dict.get('oauth_timestamp'), client_secret)
    if nonce_cache.nonce_used():
        return False, 'oauth_nonce has been used'

    if req_body_hash != req_oauth_params_dict.get('oauth_body_hash'):
        return False, 'oauth_body_hash verification failed'

    # verify the signature
    oauth_request = oauthlib.common.Request(request.build_absolute_uri(), http_method=request.method, headers=headers)
    # unfortunately, the request class is simple and we have to set the OAuth parameters manually like this
    oauth_signature = req_oauth_params_dict.pop('oauth_signature')
    # list of key-value pairs; must not include oauth_signature
    oauth_request.params = list(req_oauth_params_dict.items())
    oauth_request.signature = oauth_signature

    if not oauthlib.oauth1.rfc5849.signature.verify_hmac_sha1(oauth_request, client_secret=client_secret):
        return False, 'oauth_signature verification failed'

    return True, ''


class OAuthBodyHashAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if 'HTTP_AUTHORIZATION' not in request.META:
            return None

        data = request.data # activates the request body parser if the body has not been parsed yet
        # assume that the request was parsed with the LTI Outcome parser, so
        # the request.data contains the following keys
        exercise, user_profile = parse_sourced_id(data.get('sourced_id', ''))
        if exercise is None or user_profile is None:
            # can not find the exercise or user corresponding to the sourced id
            logger.warning('Invalid sourcedId in LTI Outcomes request: %s',
                           data.get('sourced_id', ''))
            raise AuthenticationFailed('Invalid sourcedId')
        data['exercise'] = exercise
        data['submitter'] = user_profile

        req_body_hash = data.get('body_hash')
        if not req_body_hash:
            error_msg = 'Request body hash can not be verified'
            logger.error(error_msg)
            raise AuthenticationFailed(error_msg)

        if not exercise.lti_service:
            error_msg = 'No LTI service set for the exercise'
            logger.error(error_msg)
            raise AuthenticationFailed(error_msg)

        oauth_ok, msg = verify_oauth_body_hash_and_signature(request, req_body_hash, exercise)
        if not oauth_ok:
            error_msg = 'OAuth verification failed: ' + msg
            logger.warning(error_msg)
            raise AuthenticationFailed(error_msg)

        user = LTIServiceUser(exercise=exercise, lti_service=exercise.lti_service, user_id=user_profile.user.id)
        return (user, None)
