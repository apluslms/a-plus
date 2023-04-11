from rest_framework import serializers
from rest_framework.reverse import reverse

from lib.api.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import AplusModelSerializer, AlwaysListSerializer
from userprofile.api.serializers import UserBriefSerializer, UserMinimalListField
from news.models import News

from ..models import (
    CourseInstance,
    UserTag,
    StudentGroup,
)
from ..cache.students import CachedStudent


__all__ = [
    'CourseBriefSerializer',
    'CourseListField',
    'StudentBriefSerializer',
    'CourseUsertagBriefSerializer',
    'CourseStudentGroupBriefSerializer',
    'CourseNewsBriefSerializer',
]


class CourseBriefSerializer(AplusModelSerializer):
    """
    BriefSerializer for course models
    """
    # course model has url var, so we need to redifen the type here
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


class StudentBriefSerializer(UserBriefSerializer):
    tag_slugs = serializers.SerializerMethodField()
    summary_html = serializers.SerializerMethodField()
    points = serializers.SerializerMethodField()
    data = serializers.SerializerMethodField()

    def get_tag_slugs(self, profile):
        cached = CachedStudent(self.context['view'].instance.id, profile.user.id)
        return cached.data['tag_slugs']

    def get_summary_html(self, profile):
        path = profile.get_url(self.context['view'].instance)
        return self.context['request'].build_absolute_uri(path)

    def get_points(self, profile):
        return self._get_link_lookup('api:course-points-detail', profile)

    def get_data(self, profile):
        return self._get_link_lookup('api:course-submissiondata-detail', profile)

    def _get_link_lookup(self, name, profile):
        return reverse(
            name,
            kwargs={
                'course_id': self.context['view'].instance.id,
                'user_id': profile.user.id,
            },
            request=self.context['request']
        )

    class Meta(UserBriefSerializer.Meta):
        fields = UserBriefSerializer.Meta.fields + (
            'tag_slugs',
            'summary_html',
            'points',
            'data',
        )


class CourseUsertagBriefSerializer(AplusModelSerializer):
    """
    BriefSerialzer for course UserTag objects
    """

    class Meta(AplusModelSerializer.Meta):
        model = UserTag
        fields = ('slug',)
        extra_kwargs = {
            'url': {
                'view_name': 'api:course-usertags-detail',
                'lookup_map': 'course.api.views.CourseUsertagsViewSet',
            }
        }


class CourseStudentGroupBriefSerializer(AplusModelSerializer):
    members = UserMinimalListField()

    class Meta(AplusModelSerializer.Meta):
        model = StudentGroup
        fields = (
            'members',
            'timestamp',
        )
        extra_kwargs = {
            'url': {
                'view_name': 'api:course-mygroups-detail',
            }
        }

class CourseNewsBriefSerializer(AplusModelSerializer):

    class Meta(AplusModelSerializer.Meta):
        model = News
        fields = (
            'title',
            'audience',
            'publish',
            'body',
            'pin',
        )
        extra_kwargs = {
            'url': {
                'view_name': 'api:course-news-detail',
            }
        }
