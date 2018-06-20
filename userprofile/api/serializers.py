from rest_framework import serializers
from lib.api.serializers import AplusModelSerializer, AlwaysListSerializer

from ..models import UserProfile


__all__ = [
    'UserBriefSerializer',
    'UserListField',
]


class UserBriefSerializer(AplusModelSerializer):
    # Having id, username and email as required=False and id not be read_only
    # is somewhat ugly, because when creating a new user, they actually are
    # required, and id is automatically generated. However, deserialization
    # is currently used only when creating a UserTagging, when one of id, email
    # or student_id is sufficient to identify the user, and it is easier to
    # specify them as optional here rather than try to make them optional after
    # instantiation in CourseUsertaggingsSerializer. That might have to be looked
    # into if we want to create new users using the API in the future.
    id = serializers.IntegerField(source='user.id', required=False) # NOTE: userprofile.id != user.id
    username = serializers.CharField(source='user.username', required=False)
    email = serializers.CharField(source='user.email', required=False)

    class Meta(AplusModelSerializer.Meta):
        model = UserProfile
        fields = (
            'username',
            'student_id',
            'email',
            'is_external',
        )
        extra_kwargs = {
            'url': {
                'view_name': 'api:user-detail',
                'lookup_map': 'userprofile.api.views.UserViewSet',
            }
        }


class UserListField(AlwaysListSerializer, UserBriefSerializer):
    pass
