from rest_framework import serializers, exceptions

from lib.api.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import AplusModelSerializer, NestedHyperlinkedIdentityFieldWithQuery
from exercise.api.serializers import ExerciseBriefSerializer
from userprofile.api.serializers import UserBriefSerializer, UserListField
from ..models import (
    CourseInstance,
    CourseModule,
    UserTag,
    UserTagging,
)
from exercise.models import BaseExercise
from userprofile.models import UserProfile
from .serializers import *


__all__ = [
    'CourseModuleSerializer',
    'CourseSerializer',
    'CourseStudentGroupSerializer',
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
        # List only exercises derived from BaseExercise, thus no Chapter texts (/exercise/<id> returns 404 for those)
        exercises = BaseExercise.objects.filter(course_module=obj).all()
        # FIXME: populating learning_object.parent_list() creates subqueries -> get exercise list and data from cache
        serializer = ExerciseBriefSerializer(instance=exercises, many=True, context=self.context)
        return serializer.data


class CourseSerializer(CourseBriefSerializer):
    """
    ...
    """
    exercises = NestedHyperlinkedIdentityField(view_name='api:course-exercises-list', format='html')
    points = NestedHyperlinkedIdentityField(view_name='api:course-points-list', format='html')
    students = NestedHyperlinkedIdentityField(view_name='api:course-students-list', format='html')
    taggings = NestedHyperlinkedIdentityField(view_name='api:course-taggings-list', format='html')
    usertags = NestedHyperlinkedIdentityField(view_name='api:course-usertags-list', format='html')
    my_points = NestedHyperlinkedIdentityField(
        view_name='api:course-points-detail',
        lookup_map={
            'course_id': 'id',
            'user_id': lambda o=None: 'me',
        },
    )
    my_data = NestedHyperlinkedIdentityField(
        view_name='api:course-submissiondata-detail',
        lookup_map={
            'course_id': 'id',
            'user_id': lambda o=None: 'me',
        },
    )
    data = NestedHyperlinkedIdentityField(view_name='api:course-submissiondata-list')
    aggregate_data = NestedHyperlinkedIdentityField(view_name='api:course-aggregatedata-list')
    groups = NestedHyperlinkedIdentityField(view_name='api:course-groups-list')
    my_groups = NestedHyperlinkedIdentityField(view_name='api:course-mygroups-list')

    class Meta(CourseBriefSerializer.Meta):
        fields = (
            'language',
            'starting_time',
            'ending_time',
            'visible_to_students',
            # links
            'exercises',
            'points',
            'students',
            'taggings',
            'usertags',
            'my_points',
            'my_data',
            'data',
            'aggregate_data',
            'groups',
            'my_groups',
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
            'slug',
            'description',
            'visible_to_students',
            'color',
            'font_color',
            'font_white',
            'taggings',
        )

    def validate(self, data):
        # Name is enough, slug will be automatically generated 
        data = super().validate(data)
        if not data['name']:
            raise serializers.ValidationError("At minimum, field 'name' is required")
        return data

    def create(self, validated_data):
        validated_data['course_instance_id'] = self.context['course_id']
        return super().create(validated_data)


class CourseUsertaggingsSerializer(AplusModelSerializer):
    user = UserBriefSerializer()
    tag = CourseUsertagBriefSerializer()
    _required = [ 'id', 'student_id', 'username', 'email' ]

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

    def validate(self, data):
        """
        Check that data.user has at least one of the fields in required.
        """
        user = data['user']
        if 'user' in user:
            user.update(user['user'])
            del user['user']

        for field in self._required:
            if field in user and not user[field]: del user[field]

        fields_in_user = { f for f in self._required if f in user }
        if not fields_in_user:
            raise serializers.ValidationError(
                "At least one of {} is required".format(self._required)
            )
        return data


    def create(self, validated_data):
        user_dict = validated_data['user']
        tag_dict = validated_data['tag']

        first_in_required = [ f for f in self._required if f in user_dict ][0]
        try:    
            user = {
                'id': lambda: UserProfile.objects.get(user__id=user_dict['id']),
                'student_id': lambda: UserProfile.get_by_student_id(user_dict['student_id']),
                'username': lambda: UserProfile.objects.get(user__username=user_dict['username']),
                'email': lambda: UserProfile.get_by_email(user_dict['email']),
            }[first_in_required]()
            tag = UserTag.objects.get(
               slug=tag_dict['slug'],
               course_instance=self.context['course_id']
            )
        except UserTag.DoesNotExist:
            # 404 with description
            raise exceptions.NotFound(
                 "Tag with slug {slug} was not found".format(
                     slug=tag_dict['slug']
                 )
            )
        except UserProfile.DoesNotExist:
            raise exceptions.NotFound(
                 "User identified with {key}:{value} was not found".format(
                     key=first_in_required,
                     value=user_dict[first_in_required]
                 )
            )
        obj, created = UserTagging.objects.set(user, tag)
        if not created:
            raise serializers.ValidationError(
                "User {user} already has tag {slug}".format(
                    user=user.user.username,
                    slug=tag.slug,
                )
            )
        return obj


class CourseStudentGroupSerializer(CourseStudentGroupBriefSerializer):
    members = UserListField()

    class Meta(CourseStudentGroupBriefSerializer.Meta):
        extra_kwargs = {
            'url': {
                'view_name': 'api:course-groups-detail',
            }
        }

