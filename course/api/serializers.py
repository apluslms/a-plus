from rest_framework import serializers
from rest_framework_extensions.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import HtmlViewField

from userprofile.api.serializers import UserBriefSerialiser

from ..models import (
    CourseInstance,
    CourseModule,
)
from exercise.models import BaseExercise


__all__ = [
    'LearningObjectSerializer',
    'CourseModuleSerializer',
    'CourseBriefSerializer',
    'CourseSerializer',
]


class LearningObjectSerializer(serializers.HyperlinkedModelSerializer):
    html_url = HtmlViewField()
    display_name = serializers.CharField(source='__str__')

    class Meta:
        model = BaseExercise
        fields = (
            'html_url',
            'display_name',
            'is_submittable',
        )


class CourseModuleSerializer(serializers.HyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(view_name='api:course-exercises-detail', format='html')
    html_url = HtmlViewField()
    exercises = serializers.SerializerMethodField()
    display_name = serializers.CharField(source='__str__')

    class Meta:
        model = CourseModule
        fields = (
            'url',
            'html_url',
            'display_name',
            'exercises',
            'is_open',
        )

    def get_exercises(self, obj):
        exercises = obj.flat_learning_objects(with_sub_markers=False)
        exercises = (e.as_leaf_class() for e in exercises)
        serializer = LearningObjectSerializer(instance=exercises, many=True, context=self.context)
        return serializer.data


class CourseBriefSerializer(serializers.HyperlinkedModelSerializer):
    """
    ...
    """
    url = NestedHyperlinkedIdentityField(view_name='api:course-detail', format='html')
    html_url = HtmlViewField()
    course_id = serializers.IntegerField(source='id')
    course_code = serializers.CharField(source='course.code')
    course_name = serializers.CharField(source='course.name')

    class Meta:
        model = CourseInstance
        fields = (
            'url',
            'html_url',
            'course_id',
            'course_code',
            'course_name',
            'instance_name',
        )

class CourseSerializer(CourseBriefSerializer):
    """
    ...
    """
    exercises = NestedHyperlinkedIdentityField(view_name='api:course-exercises-list', format='html')
    students = NestedHyperlinkedIdentityField(view_name='api:course-students-list', format='html')
    points = NestedHyperlinkedIdentityField(view_name='api:course-points-list', format='html')

    class Meta(CourseBriefSerializer.Meta):
        fields = CourseBriefSerializer.Meta.fields + (
            'starting_time',
            'ending_time',
            'exercises',
            'students',
            'points',
        )
