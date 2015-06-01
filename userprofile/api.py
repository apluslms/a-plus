from api.permissions import SuperuserAuthorization
from tastypie.resources import ModelResource
from userprofile.models import UserProfile


class UserProfileResource(ModelResource):
    
    def dehydrate(self, bundle):
        """
        This method adds fields from the corresponding User
        object to the response.
        """
        user = bundle.obj.user
        extra_fields = {"username":     user.username,
                        "first_name":   user.first_name,
                        "last_name":    user.last_name,
                        "email":        user.email,
                        }
        bundle.data.update(extra_fields)
        return bundle

    class Meta:
        queryset = UserProfile.objects.all()
        resource_name = 'userprofile'

        # In this version of the API only superusers are allowed to access
        # userprofile objects
        allowed_methods = ['get']
        authorization = SuperuserAuthorization()
