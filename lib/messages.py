from django.contrib import messages
from django.http import HttpRequest
from rest_framework.request import Request

def error(request, *args, **kwargs):
    # Skip messages generated under API
    #if isinstance(request, Request):
    #    request = request._request
    if isinstance(request, HttpRequest):
        messages.error(request, *args, **kwargs)
