from tastypie.authorization import Authorization


class SuperuserAuthorization(Authorization):
    
    def is_authorized(self, request, object=None):
        return request.user.is_superuser

    def apply_limits(self, request, object_list):
        return object_list
