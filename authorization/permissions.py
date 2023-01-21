"""
Base permission classes.

These classes use same interface than ones in django-rest-framework and
are usable with APIViews too.
"""
import string
import logging
from typing import List
from abc import ABC, abstractmethod

from django.conf import settings
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.http import HttpRequest
from rest_framework.permissions import BasePermission as Permission

import jwt

from lib.helpers import Enum


SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
logger = logging.getLogger('aplus.authorization')


class FilterBackend:
    """
    FilterBackend interface
    """
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        raise NotImplementedError

    def get_fields(self, view): # pylint: disable=unused-argument
        return []


class NoPermission(Permission):
    """
    Base Permission class that gives no access permission to anyone.
    """
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


class MessageMixin:
    """
    Adds easy way to specify what exactly caused the PermissionDenied
    """
    def error_msg(self, message: str, delim=None, format=None, replace=False): # pylint: disable=redefined-builtin
        """
        Add extra text to self.message about the reason why permission
        was denied. Uses lazy object so the message string is evaluated
        only when rendered.

        If optional argument `format` is given, then it's used with format_lazy
        to format the message with the dictionary arguments from `format` arg.

        Optional argument `delim` can be used to change the string used to join
        self.message and `message`.

        If optional argument `replace` is true, then self.message is replaced with
        the `message`.
        """
        if delim is None:
            delim = ': '

        if format:
            message = format_lazy(message, **format)

        if replace:
            self.message = message
        else:
            assert 'message' not in self.__dict__, (
                "You are calling error_msg without replace=True "
                "after calling it with it first. Fix your code by removing "
                "the first method call and add replace=True to the second method call too."
            )
            msg_without_end_punctuation = (
                self.message[0:-1] if self.message[-1] in string.punctuation
                else self.message
            )
            self.message = format_lazy(
                '{}{}{}',
                msg_without_end_punctuation,
                delim,
                message,
            )


# Access mode
# ===========

# All access levels
ACCESS = Enum(
    ('ANONYMOUS', 0, _('ACCESS_ANYONE')),
    ('ENROLL', 1, None),
    ('STUDENT', 3, _('ACCESS_ANY_STUDENT')),
    ('ENROLLED', 4, _('ACCESS_ENROLLED_STUDENT')),
    ('ASSISTANT', 5, _('ACCESS_COURSE_ASSISTANT')),
    ('GRADING', 6, _('ACCESS_GRADING')),
    ('TEACHER', 10, _('ACCESS_TEACHER')),
    ('SUPERUSER', 100, _('ACCESS_SUPERUSER')),
)


class AccessModePermission(MessageMixin, Permission):
    """
    If view has access_mode that is not anonymous, then require authentication
    """
    message = _('ACCESS_PERMISSION_DENIED_MSG')

    def has_permission(self, request, view):
        access_mode = view.get_access_mode()

        if access_mode == ACCESS.ANONYMOUS:
            return True
        if not request.user.is_authenticated:
            self.error_msg(_('ACCESS_ERROR_ONLY_AUTHENTICATED'))
            return False

        if access_mode >= ACCESS.SUPERUSER:
            return request.user.is_superuser

        if access_mode >= ACCESS.TEACHER:
            if not view.is_teacher:
                self.error_msg(_('ACCESS_ERROR_ONLY_TEACHERS'))
                return False

        elif access_mode >= ACCESS.ASSISTANT:
            if not view.is_course_staff:
                self.error_msg(_('ACCESS_ERROR_ONLY_COURSE_STAFF'))
                return False

        elif access_mode == ACCESS.ENROLLED:
            if not view.is_course_staff and not view.is_student:
                self.error_msg(_('ACCESS_ERROR_ONLY_ENROLLED_STUDENTS'))
                return False

        return True


# Object permissions
# ==================


class ObjectVisibleBasePermission(MessageMixin, Permission):
    model = None
    obj_var = None

    def has_permission(self, request, view):
        obj = getattr(view, self.obj_var, None)
        return (
            obj is None or
            self.has_object_permission(request, view, obj)
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        return (
            # skip objects that are not the model in question
            not isinstance(obj, self.model) or # pylint: disable=isinstance-second-argument-not-valid-type
            user.is_staff or
            user.is_superuser or
            self.is_object_visible(request, view, obj)
        )

    def is_object_visible(self, request, view, obj):
        raise NotImplementedError


class OAuth2ScopeChecker(ABC):
    '''
    To be inherited by View classes that wish to use OAuth2.
    Defines check_token_scope to verify if provided bearer token has
    sufficient privileges to access the view.
    '''
    @abstractmethod
    def check_token_scope(self, scopes: List[str]) -> bool:
        '''
        Returns true if the scope(s) required by the current view is included in the
        given scopes list.
        '''


class OAuth2TokenPermission(Permission):
    '''
    Permission controlled by OAuth2 Bearer tokens.
    '''
    def has_permission(self, request: HttpRequest, view: OAuth2ScopeChecker) -> bool:
        token = request.headers.get('Authorization')
        if not token:
            logger.warning("Missing authorization token")
            return False
        token = token.split(' ')
        if len(token) < 2:
            logger.warning("Invalid authorization token")
            return False
        token = token[1]

        # Check if token is known and is valid for the purpose
        pemkey = settings.APLUS_AUTH_LOCAL['PUBLIC_KEY']
        try:
            data = jwt.decode(
                token,
                pemkey,
                algorithms=["RS256"],
            )
        except (jwt.exceptions.InvalidSignatureError, jwt.ExpiredSignatureError, jwt.InvalidAudienceError) as e:
            logger.error("LTI 1.3: Bearer token decoding failed: %s", str(e))
            return False

        if not view.check_token_scope(data.get('scope', '').split()):
            logger.warning("Insufficient bearer token scope: %s", token)
            return False

        return True
