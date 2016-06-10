from rest_framework import serializers

from ..models import Course, CourseInstance


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ('name', 'url')

class CourseInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseInstance
        fields = ('instance_name', 'url', 'course')
