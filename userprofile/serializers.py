from userprofile.models import UserProfile
from django.contrib.auth.models import User
from rest_framework import serializers


class UserPSerializer(serializers.ModelSerializer):
    """"
    Add the details of a user. This has to be done here because
    details are in User-model, not in UserProfile which has OneToOneField
    to a User-model
    """
    username = serializers.CharField(source='user.username')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.CharField(source='user.email')

    class Meta:
        model = UserProfile
        fields = ('user', 'student_id', 'username', 'first_name', 'last_name',
                  'email')
