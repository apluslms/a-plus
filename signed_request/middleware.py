"""
The signed_request package was initially developed in A+ with the intention
to use it for authenticating users on external services. However, this idea was 
later abandoned and the OAuth protocol was used instead. 
"""

from django.conf import settings
from django.middleware.common import CommonMiddleware
from django.shortcuts import redirect
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.auth import login

from django.contrib.auth.models import User

import base64
import urllib
import time
import hmac
import json

REQUIRED_PARAMETERS = ("username", "first_name", "last_name", "is_staff", "context", "timestamp")
SHARED_SECRET       = "abcd1234"


class SignedRequestLoginMiddleware(object):
    
    def process_request(self, request):
        if "signed_request_payload" not in request.REQUEST or "signed_request_signature" not in request.REQUEST:
            return None
        
        data64              = request.REQUEST["signed_request_payload"]
        signature           = request.REQUEST["signed_request_signature"]
        
        try:
            # Verify the signature
            if hmac.new(SHARED_SECRET, data64).hexdigest() != signature:
                return HttpResponseForbidden('<h1>Forbidden</h1>')
            
            data            = base64.b64decode(data64)
            user_dict       = json.loads(data)
        except:
            return HttpResponseBadRequest("Reading signature failed.")
        
        for param in REQUIRED_PARAMETERS:
            if param not in user_dict:
                return HttpResponseBadRequest("Missing parameter " + param)
        
        signed_timestamp    = user_dict["timestamp"]
        
        # Make sure timestamp is current
        current_timestamp   = int(time.time())
        
        # Check that the timestamp is no older than 120 seconds
        if abs(current_timestamp - signed_timestamp) > 120:
            return HttpResponseForbidden('<h1>Expired</h1><p>The link you used has expired or the system clock is inaccurate.</p>')
        
        try:
            user            = User.objects.get(username=user_dict["username"])
        except:
            user            = User(username=user_dict["username"])
        user.first_name     = user_dict["first_name"]
        user.last_name      = user_dict["last_name"]
        user.is_staff       = user_dict["is_staff"]
        
        user.save()
        
        user.backend        = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        
        get_params          = request.GET.copy()
        del get_params["signed_request_payload"]
        del get_params["signed_request_signature"]
        
        return redirect(request.path + "?" + urllib.urlencode(get_params))

