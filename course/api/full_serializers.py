from rest_framework import serializers
from rest_framework_extensions.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import AplusModelSerializer

from exercise.api.serializers import ExerciseBriefSerializer
from ..models import CourseModule
from .serializers import CourseBriefSerializer


__all__ = [
    'CourseModuleSerializer',
    'CourseSerializer',
]


class CourseModuleSerializer(AplusModelSerializer):
    url = NestedHyperlinkedIdentityField(view_name='api:course-exercises-detail')
    exercises = serializers.SerializerMethodField()
    display_name = serializers.CharField(source='__str__')

    class Meta(AplusModelSerializer.Meta):
        model = CourseModule
        fields = (
            'url',
            'html_url',
            'display_name',
            'is_open',
            'exercises',
        )

    def get_exercises(self, obj):
        # this needs to be method so .as_leaf_class() can be called
        exercises = obj.learning_objects.all()
        exercises = (e.as_leaf_class() for e in exercises)
        serializer = ExerciseBriefSerializer(instance=exercises, many=True, context=self.context)
        return serializer.data


class CourseSerializer(CourseBriefSerializer):
    """
    ...
    """
    exercises = NestedHyperlinkedIdentityField(view_name='api:course-exercises-list', format='html')
    students = NestedHyperlinkedIdentityField(view_name='api:course-students-list', format='html')
    # FIXME: points endpoint is disabled
    #points = NestedHyperlinkedIdentityField(view_name='api:course-points-list', format='html')

    class Meta(CourseBriefSerializer.Meta):
        fields = (
            'language',
            'starting_time',
            'ending_time',
            'visible_to_students',
            'exercises',
            'students',
            #'points',
        )
