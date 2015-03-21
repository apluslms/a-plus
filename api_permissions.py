# Tastypie
from tastypie.resources import ModelResource
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization


class CIStaffAuthorization(Authorization):
    """ Limits the access to only users, who have authenticated
        and to CourseInstances that they are either assistants 
        or teachers in. """
    
    def is_authorized(self, request, object=None):
        return request.user.is_authenticated
    
    def apply_limits(self, request, object_list):
        if request.user.is_superuser:
            # Super users have access to all course instances
            return object_list
        else:
            # Other users have access to course instances they are 
            # teachers or assistants at
            userprofile = request.user.userprofile
            return userprofile.get_courseinstance_staff_queryset.all()


class SuperuserAuthorization(Authorization):
    def is_authorized(self, request, object=None):
        return request.user.is_superuser
    
    def apply_limits(self, request, object_list):
        return object_list
    

class StaffAuthentication(Authentication):
    def is_authenticated(self, request, **kwargs):
        return request.user.is_staff


class CourseAuthentication(Authentication):
    pass


class CourseAuthorization(Authorization):
    def is_authorized(self, request, object=None):
        return request.user.is_authenticated
    
    def apply_limits(self, request, object_list):
        if request and hasattr(request, 'user'):
            return object_list.filter(author__username=request.user.username)
        return object_list.none()

