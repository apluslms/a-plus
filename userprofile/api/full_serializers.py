from rest_framework.fields import SerializerMethodField
from rest_framework import serializers

from course.api.serializers import CourseBriefSerializer
from course.models import CourseInstance
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
    enrolled_courses = SerializerMethodField()
    staff_courses = SerializerMethodField()
    teacher_courses = SerializerMethodField()
    assistant_courses = SerializerMethodField()

    class Meta(UserBriefSerializer.Meta):
        fields = (
            'enrolled_courses',
            'staff_courses',
            'teacher_courses',
            'assistant_courses',
            'student_id',
            'full_name',
            'first_name',
            'last_name',
            'email',
        )

    def get_enrolled_courses(self, obj):
        courses = CourseInstance.objects.get_enrolled(obj)
        serializer = CourseBriefSerializer(instance=courses, many=True, context=self.context)
        return serializer.data

    def get_staff_courses(self, obj):
        teacher_courses = CourseInstance.objects.get_teaching(obj)
        assistant_courses = CourseInstance.objects.get_assisting(obj)
        staff_courses = teacher_courses | assistant_courses
        serializer = CourseBriefSerializer(instance=staff_courses, many=True, context=self.context)
        return serializer.data

    def get_teacher_courses(self, obj):
        teacher_courses = CourseInstance.objects.get_teaching(obj)
        serializer = CourseBriefSerializer(instance=teacher_courses, many=True, context=self.context)
        return serializer.data

    def get_assistant_courses(self, obj):
        assistant_courses = CourseInstance.objects.get_assisting(obj)
        serializer = CourseBriefSerializer(instance=assistant_courses, many=True, context=self.context)
        return serializer.data
