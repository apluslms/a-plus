from rest_framework import serializers
from course.models import CourseInstance
from ..models import UserProfile


class UserBriefSerialiser(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        source='user.id',
        view_name='api:user-detail',
        lookup_url_kwarg='user_id',
        format='html',
    )
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')

    def list_courses(self, userinstance):
      # Get courses where the user is enrolled
      enrolled_courses = []
      course_instances = CourseInstance.objects.all()
      for course in course_instances:
          if userinstance in course.students.all():
              enrolled_courses.append(course.__str__())

      # Convert list to str and return result
      return ", ".join(enrolled_courses)

    class Meta:
        model = UserProfile
        fields = (
            'url',
            'courses',
            'user_id',
            'username'
        )

class UserSerializer(UserBriefSerialiser):
    """
    Add the details of a user.
    """

    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.CharField(source='user.email')

    class Meta(UserBriefSerialiser.Meta):
        fields = UserBriefSerialiser.Meta.fields + (
            'student_id',
            'first_name',
            'last_name',
            'email',
        )
