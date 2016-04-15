from tastypie.authorization import Authorization
from tastypie.exceptions import Unauthorized


class SuperuserAuthorization(Authorization):

    # This implementation is supported only in versions 0.9.11 and below...
    """
    def is_authorized(self, request, object=None):
        return request.user.is_superuser

    def apply_limits(self, request, object_list):
        return object_list"""

    # Implementation in versions 0.9.12 and up.
    def read_list(self, object_list, bundle):
        # Is the person who made the request, superuser?
        if bundle.request.user.is_superuser:
            return object_list
        else:
            raise Unauthorized("Sorry, only VIP.")
