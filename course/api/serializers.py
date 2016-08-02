from rest_framework import serializers
from rest_framework_extensions.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import AplusModelSerializer, AlwaysListSerializer

from ..models import (
    CourseInstance,
    CourseModule,
)


__all__ = [
    'CourseBriefSerializer',
    'CourseListField',
]


class CourseBriefSerializer(AplusModelSerializer):
    """
    ...
    """
    url = NestedHyperlinkedIdentityField(
        view_name='api:course-detail',
        lookup_map='course.api.views.CourseViewSet'
    )
    code = serializers.CharField(source='course.code')
    name = serializers.CharField(source='course.name')

    class Meta(AplusModelSerializer.Meta):
        model = CourseInstance
        fields = (
            'url',
            'html_url',
            'code',
            'name',
            'instance_name',
        )


class CourseListField(AlwaysListSerializer, CourseBriefSerializer):
    pass
