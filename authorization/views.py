from django.http import HttpResponse

try:
    from django.contrib.auth.mixins import AccessMixin
except ImportError:
    from .djangobackports import AccessMixin_1_10 as AccessMixin

from .exceptions import ValidationFailed
from .permissions import NoPermission


class AuthenticationMixin(AccessMixin):
    def perform_authentication(self):
        """
        Perform authentication on the incoming request.
        Note that if you override this and simply 'pass', then authentication
        will instead be performed lazily, the first time either
        `request.user` or `request.auth` is accessed.
        """
        self.request.user

    def handle_no_permission(self):
        if self.request.user.is_authenticated():
            self.raise_exception = True
        return super(AuthenticationMixin, self).handle_no_permission()

    def validate_request(self):
        self.perform_authentication()
        super().validate_request()


class AuthorizationMixin(object):
    """
    Authorization mixin adds components to handle access control restrictions
    to different views.
    This mixin expect common django View stack and hooks in via dispatch() method.

    This class has a lot of influence from django-rest-framework
    """
    permission_classes = [NoPermission]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        return (Permission() for Permission in self.permission_classes)

    def permission_denied(self, message=None):
        if not self.permission_denied_message:
            self.permission_denied_message = message
        raise ValidationFailed(self.handle_no_permission())

    def check_permissions(self):
        """
        Check if the request should be permitted.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            if not permission.has_permission(self.request, self):
                message = getattr(permission, 'message', None)
                self.permission_denied(message)

    def check_object_permissions(self, obj):
        """
        Check if the request should be permitted for a given object.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                message = getattr(permission, 'message', None)
                self.permission_denied(message)

    def validate_request(self):
        self.check_permissions()
        super().validate_request()


class ResourceMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__attr = []

    def get_resource_objects(self):
        """
        Get the resource objects sufficient to determine the existance.
        Should raise Http404 if the request does not reach a resource.
        Use self.note to announce attributes of further interest.
        """
        pass

    def get_common_objects(self):
        """
        Once access is verified further objects may be created that
        are common for different HTTP methods, e.g. get and post.
        Use self.note to announce attributes of further interest.
        """
        pass

    def note(self, *args):
        """
        The class attribute names given in argument list are marked
        "interesting" for the view. In a TemplateView these will be
        injected to the template context.
        """
        self.__attr.extend(args)

    def get_context_data(self, **kwargs):
        context = {"request": self.request}
        for key in self.__attr:
            context[key] = getattr(self, key)
        context.update(kwargs)
        return super().get_context_data(**context)


    def validate_request(self):
        self.get_resource_objects()
        super().validate_request()

    def dispatch(self, request, *args, **kwargs):
        self.get_common_objects()
        return super().dispatch(request, *args, **kwargs)


class AuthorizedResourceBase(object):
    def validate_request(self):
        """
        Validate request before doing dispatch for it.
        raise ValidationFailed if request is not valid.
        """
        pass


class AuthorizedResourceMixin(AuthenticationMixin,
                              ResourceMixin,
                              AuthorizationMixin,
                              AuthorizedResourceBase):
    """
    AuthorizedResourceMixin handles correct ordering of actions in
    Authentication and Authorization chain with required resource objects loaded
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Hook to dispatch chain. This method is called before View.dispatch
        routes the http method call to actual handler
        """
        # do authentication and authorization tasks before resuming dispatch
        # process. Dispatching can be skipped with an exception.
        # Validate chain should be:
        # -> AuthenticationMixin: do authentication tasks
        # -> ResourceMixin: load resource objects used in authorization
        # -> AuthorizationMixin: check permissions
        try:
            self.validate_request()
        except ValidationFailed as exc:
            return exc.response
        # Dispath will continue with:
        # -> ResourceMixin: load resource objects used in view
        return super().dispatch(request, *args, **kwargs)