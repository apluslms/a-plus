from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.messages import error as error_message
from django.core.exceptions import PermissionDenied

from .exceptions import ValidationFailed
from .permissions import NoPermission


class AuthDispatchBase:

    def initialize_request(self, request, *args, **kwargs):
        return request

    def validate_request(self, request, *args, **kwargs):
        pass

    def handle_exception(self, exc):
        if isinstance(exc, ValidationFailed):
            return exc.response
        raise exc

    def dispatch(self, request, *args, **kwargs):
        """
        Hook to dispatch chain. This method is called before View.dispatch
        routes the http method call to actual handler (done by super().dispatch())
        """
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request

        try:
            # request validation takes care of authentication and authorization
            self.validate_request(request, *args, **kwargs)

            # handle the actual http method
            response = super().dispatch(request, *args, **kwargs)
        except Exception as exc:
            response = self.handle_exception(exc)

        return response


class AuthenticationMixin(AccessMixin):
    def perform_authentication(self, request):
        """
        Perform authentication on the incoming request.
        Note that if you override this and simply 'pass', then authentication
        will instead be performed lazily, the first time either
        `request.user` or `request.auth` is accessed.
        """
        request.user # pylint: disable=pointless-statement

    def handle_no_permission(self):
        """
        Will be called by self.permission_denied() when user doesn't
        have permission.

        This method has logic copied from
          django.contrib.auth.mixins.AccessMixin.handle_no_permission()
        """
        request = self.request
        message = self.get_permission_denied_message()

        # Add message to messages interface, so it will be rendered
        # on login and error pages
        error_message(request, message)

        # For authenticated users, raise exception.
        if request.user.is_authenticated:
            raise PermissionDenied(message)

        # Redirect not authenticated users to login
        return redirect_to_login(request.get_full_path(),
                                    self.get_login_url(),
                                    self.get_redirect_field_name())

    def validate_request(self, request, *args, **kwargs):
        self.perform_authentication(request)
        super().validate_request(request, *args, **kwargs)


class AuthorizationMixin:
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
        return [Permission() for Permission in self.permission_classes]

    def permission_denied(self, message=None):
        if not self.permission_denied_message:
            self.permission_denied_message = message
        raise ValidationFailed(self.handle_no_permission())

    def check_permissions(self, request):
        """
        Check if the request should be permitted.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                message = getattr(permission, 'message', None)
                self.permission_denied(message)

    def check_object_permissions(self, request, obj):
        """
        Check if the request should be permitted for a given object.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                message = getattr(permission, 'message', None)
                self.permission_denied(message)

    def validate_request(self, request, *args, **kwargs):
        self.check_permissions(request)
        super().validate_request(request, *args, **kwargs)


class ResourceMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__attr = []

    def get_resource_objects(self):
        """
        Get the resource objects sufficient to determine the existance.
        Should raise Http404 if the request does not reach a resource.
        Use self.note to announce attributes of further interest.
        """

    def get_common_objects(self):
        """
        Once access is verified further objects may be created that
        are common for different HTTP methods, e.g. get and post.
        Use self.note to announce attributes of further interest.
        """

    def note(self, *args):
        """
        The class attribute names given in argument list are marked
        "interesting" for the view. In a TemplateView these will be
        injected to the template context.
        """
        self.__attr.extend(args)

    def get_context_data(self, **kwargs):
        """
        Add member variables recorded with .note() to context_data
        """
        context = {"request": self.request}
        for key in self.__attr:
            context[key] = getattr(self, key)
        context.update(kwargs)
        return super().get_context_data(**context)

    def validate_request(self, request, *args, **kwargs):
        """
        Call .get_resource_objects before .validate_request()
        Call .get_common_objects() after .validate_request()
        """
        self.get_resource_objects()
        super().validate_request(request, *args, **kwargs)
        self.get_common_objects()


class AuthorizedResourceMixin(AuthenticationMixin,
                              ResourceMixin,
                              AuthorizationMixin,
                              AuthDispatchBase):
    """
    AuthorizedResourceMixin handles correct ordering of actions in
    Authentication and Authorization chain with required resource objects loaded

    call order:
     - AuthenticationMixin.perform_authentication()  Make sure we have user
     - ResourceMixin.get_resource_objects()          Load resource objects used for authorization
     - AuthorizationMixin.check_permissions()        Check authorization using permissions
     - ResourceMixin.get_common_objects()            Load common resources after accepted control
    """

    # Used to debug call order and to make sure it is correct
    #_ident = 0
    #def __getattribute__(self, key):
    #    val = super().__getattribute__(key)
    #    if callable(val):
    #        def wrap(*args, **kwargs):
    #            print(" %s--> calling %s" % ("  "*self._ident, val.__name__,))
    #            self._ident += 1
    #            try:
    #                ret = val(*args, **kwargs)
    #            except Exception as e:
    #                self._ident -= 1
    #                print(" %s<-- except  %s : %s" % ("  "*self._ident, val.__name__, e.__class__.__name__))
    #                raise
    #            self._ident -= 1
    #            print(" %s<-- return  %s" % ("  "*self._ident, val.__name__,))
    #            return ret
    #        return wrap
    #    return val
