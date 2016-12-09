from rest_framework import serializers
from rest_framework_extensions.fields import NestedHyperlinkedIdentityField

from lib.api.serializers import AplusModelSerializer, NestedHyperlinkedIdentityFieldWithQuery
from exercise.api.serializers import ExerciseBriefSerializer
from userprofile.api.serializers import UserBriefSerializer
from ..models import (
    CourseModule,
    UserTag,
    UserTagging,
)
from .serializers import *


__all__ = [
    'CourseModuleSerializer',
    'CourseSerializer',
    'CourseUsertagSerializer',
    'CourseUsertaggingsSerializer',
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
    usertags = NestedHyperlinkedIdentityField(view_name='api:course-usertags-list', format='html')
    taggings = NestedHyperlinkedIdentityField(view_name='api:course-taggings-list', format='html')
    points = NestedHyperlinkedIdentityField(view_name='api:course-points-list', format='html')
    submissiondata = NestedHyperlinkedIdentityField(view_name='api:course-submissiondata-list', format='html')

    class Meta(CourseBriefSerializer.Meta):
        fields = (
            'language',
            'starting_time',
            'ending_time',
            'visible_to_students',
            'exercises',
            'students',
            'usertags',
            'taggings',
            'points',
            'submissiondata',
        )


class CourseUsertagSerializer(CourseUsertagBriefSerializer):
    """
    Full Serializer for UserTag model
    """
    taggings = NestedHyperlinkedIdentityFieldWithQuery(
        view_name='api:course-taggings-list',
        lookup_map={ 'course_id': 'course_instance_id' },
        query_params={ 'tag_id': 'id' },
    )

    class Meta(CourseUsertagBriefSerializer.Meta):
        model = UserTag
        fields = (
            'name',
            'description',
            'visible_to_students',
            'color',
            'font_color',
            'taggings',
        )


class CourseUsertaggingsSerializer(AplusModelSerializer):
    user = UserBriefSerializer()
    tag = CourseUsertagBriefSerializer()

    class Meta(AplusModelSerializer.Meta):
        model = UserTagging
        fields = (
            'user',
            'tag',
        )
        extra_kwargs = {
            'url': {
                'view_name': 'api:course-taggings-detail',
            }
        }
