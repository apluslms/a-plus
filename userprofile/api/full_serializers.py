from rest_framework import serializers
from lib.api.serializers import AplusModelSerializer

from course.api.serializers import CourseListField
from .serializers import UserBriefSerializer


__all__ = [
    'UserSerializer',
]


class UserSerializer(UserBriefSerializer):
    """
    Add the details of a user.
    """

    full_name = serializers.CharField(source='user.get_full_name')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.CharField(source='user.email')
    enrolled_courses = CourseListField(source='enrolled')

    class Meta(UserBriefSerializer.Meta):
        fields = (
            'enrolled_courses',
            'student_id',
            'full_name',
            'first_name',
            'last_name',
            'email',
        )
