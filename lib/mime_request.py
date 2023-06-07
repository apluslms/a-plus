from __future__ import annotations
import functools
from typing import Any, cast, List, Optional, Type

from django.http import HttpRequest

_mime_request_classes = {}
def _mime_request_class(request: HttpRequest) -> Type[MIMERequest]:
    """Return a MIMERequest class with the request's class as a parent class"""
    if request.__class__ not in _mime_request_classes:
        class _MIMERequest(MIMERequest, request.__class__):
            ...

        _mime_request_classes[request.__class__] = _MIMERequest

    return _mime_request_classes[request.__class__]


class MIMERequest(HttpRequest):
    """Django HttpRequest but with <expected_mime> field. See accepts_mimes(...)"""
    expected_mime: str

    def __init__(self):
        raise NotImplementedError("__init__() is not implemented. Use cast() instead.")

    @staticmethod
    def cast(request: HttpRequest, acceptable_mimes: List[str]) -> MIMERequest:
        """Cast the given request to a MIMERequest, and return it.

        Note that this changes the type of given original request to MIMERequest.
        """
        # Some trickery to add expected_mime to the request and change the type
        # _mime_request_class is required because the request class is different
        # depending on the situation. E.g. WSGIRequest vs HttpRequest
        request.__class__ = _mime_request_class(request)
        request = cast(MIMERequest, request)
        request.expected_mime = accepted_mime(acceptable_mimes, request.headers.get("Accept"))
        return request


def accepts_mimes(acceptable: List[str]):
    """Function/method decorator that changes the request object type to MIMERequest.

    :param acceptable: list of acceptable mime types

    The request object will have a <expected_mime> attribute with the mime type
    that the client expects the response to be in. See accepted_mime(...) for
    how the mime type is chosen.
    """
    # We need a class so that the decorator can be applied to both functions and methods
    class SignatureChooser(object):
        def __init__(self, func):
            self.func = func
            functools.wraps(func)(self)
        def __call__(self, request, *args, **kwargs):
            """Normal function call. This is called if self.func is a function"""
            return self.call_with_mime(None, request, *args, **kwargs)
        def __get__(self, instance: Optional[Any], _):
            """Return class instance method. This is called if self.func is a method"""
            return functools.partial(self.call_with_mime, instance)
        def call_with_mime(self, obj: Optional[Any], request: HttpRequest, *args, **kwargs):
            request = MIMERequest.cast(request, acceptable)
            if obj is None:
                return self.func(request, *args, **kwargs)
            else:
                return self.func(obj, request, *args, **kwargs)

    return SignatureChooser


def accepted_mime(acceptable: List[str], accept_header: Optional[str]):
    """Return which mime type in <acceptable> matches <accept_header> first.

    Match priority order is the following:
    1. Exact match over a wild card match
    2. Earlier types in <acceptable> are prioritized

    Defaults to the first item in <acceptable> if no match was found.

    For example,
        accepted_mime(["text/html", "application/json"], "text/*, application/json")
    and
        accepted_mime(["text/html", "application/json"], "application/*")
    will return "application/json" but
        accepted_mime(["text/html", "application/json"], "text/html, application/json")
    and
        accepted_mime(["text/html", "application/json"], "text/*, application/*")
    will return "text/html".
    """
    if accept_header is None or len(acceptable) == 1:
        return acceptable[0]

    accepts = [mime.split(";")[0].strip() for mime in accept_header.split(",")]

    # Check for exact match first
    for mime in acceptable:
        if mime in accepts:
            return mime

    # Check for wildcard match
    for mime in acceptable:
        mime.split("/")
        if f"{mime[0]}/*" in accepts or f"*/{mime[1]}" in accepts:
            return mime

    # Default to first element
    return acceptable[0]
