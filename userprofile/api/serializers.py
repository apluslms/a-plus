from rest_framework import serializers

from course.models import CourseInstance
from ..models import UserProfile


__all__ = [
    'UserBriefSerialiser',
    'UserSerializer',
]


class UserBriefSerialiser(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        source='user.id',
        view_name='api:user-detail',
        lookup_url_kwarg='user_id',
        format='html',
    )
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')

    class Meta:
        model = UserProfile
        fields = (
            'url',
            'user_id',
            'username'
        )

class UserSerializer(UserBriefSerialiser):
    """
    Add the details of a user.
    """

    courses = serializers.SerializerMethodField('list_courses')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.CharField(source='user.email')

    def list_courses(self, userinstance):
      # Get courses where the user is enrolled
      enrolled_courses = []
      for enrolled in userinstance.enrolled.all():
          enrolled_courses.append({
            "name": enrolled.__str__(),
            "id": enrolled.id
          })

      # Return all coursetuples in list. Tuple consists of name of the course
      # and the id of the course
      return enrolled_courses

    class Meta(UserBriefSerialiser.Meta):
        fields = UserBriefSerialiser.Meta.fields + (
            'courses',
            'student_id',
            'first_name',
            'last_name',
            'email',
        )
