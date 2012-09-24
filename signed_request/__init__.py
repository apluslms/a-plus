"""
The signed_request package was initially developed in A+ with the intention
to use it for authenticating users on external services. However, this idea was 
later abandoned and the OAuth protocol was used instead. 
"""

import base64
import time
import hmac

from django.utils import simplejson

def create_request(user, shared_secret, context="undefined"):
    """
    Creates a request for the given user and signs it with
    a shared secret. 
    
    @param user: a Django user who will make the request
    @param shared_secret: a secret string known by the signing party and the target service
    @param context: any string describing the context of the request 
    @return: a tuple with base64 encoded representation of the request payload and a hexadecimal signature
    """
    params = {"username"    : user.username, 
              "first_name"  : user.first_name,
              "last_name"   : user.last_name,
              "is_staff"    : user.is_staff,
              "context"     : "test"}
    
    return sign_request(params, shared_secret)

def sign_request(params, shared_secret):
    """
    Signs the given request dictionary with the given shared secret
    
    @param params: the parameters to be included in the request 
    @param shared_secret: a secret string known by the signing party and the target service
    @return: a tuple with base64 encoded representation of the request payload and a hexadecimal signature
    """
    
    params["timestamp"] = int(time.time())
    payload             = base64.b64encode(simplejson.dumps(params))
    signature           = hmac.new(shared_secret, payload).hexdigest()
    return payload, signature