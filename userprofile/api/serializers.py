from rest_framework import serializers
from course.models import CourseInstance
from ..models import UserProfile


class UserSerializer(serializers.HyperlinkedModelSerializer):
    """"
    Add the details of a user. This has to be done here because
    details are in User-model, not in UserProfile which has OneToOneField
    to a User-model
    """
    courses = serializers.SerializerMethodField('list_courses')
    url = serializers.HyperlinkedIdentityField(view_name='api:user-detail', lookup_field='user_id', format='html')
    user_id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.CharField(source='user.email')

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
            'student_id',
            'username',
            'first_name',
            'last_name',
            'email',
            )
