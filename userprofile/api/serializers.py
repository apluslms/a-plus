from rest_framework import serializers

from ..models import UserProfile


class UserSerializer(serializers.HyperlinkedModelSerializer):
    """"
    Add the details of a user. This has to be done here because
    details are in User-model, not in UserProfile which has OneToOneField
    to a User-model
    """
    url = serializers.HyperlinkedIdentityField(view_name='api:user-detail', lookup_field='user_id', format='html')
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.CharField(source='user.email')

    class Meta:
        model = UserProfile
        fields = (
            'url',
            'user_id',
            'student_id',
            'username',
            'first_name',
            'last_name',
            'email',
            )
