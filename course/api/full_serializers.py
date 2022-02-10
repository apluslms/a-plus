from typing import OrderedDict
from rest_framework import serializers, exceptions

from lib.api.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import AplusModelSerializer, NestedHyperlinkedIdentityFieldWithQuery
from exercise.api.full_serializers import TreeExerciseSerializer
from exercise.api.serializers import ExerciseBriefSerializer
from userprofile.api.serializers import UserBriefSerializer, UserListField
from django.contrib.auth.models import User
from ..models import (
    CourseInstance,
    Course,
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
    'CourseWriteSerializer',
    'CourseStudentGroupSerializer',
    'CourseUsertagSerializer',
    'CourseUsertaggingsSerializer',
    'TreeCourseModuleSerializer',
    'CourseNewsSerializer',
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

    def get_exercises(self, obj: CourseModule) -> OrderedDict:
        # List only exercises derived from BaseExercise, thus no Chapter texts (/exercise/<id> returns 404 for those)
        # Check if the exercises were prefetched in the view
        if hasattr(obj, 'exercises'):
            exercises = obj.exercises
        else:
            exercises = BaseExercise.objects.filter(course_module=obj).all()
        serializer = ExerciseBriefSerializer(instance=exercises, many=True, context=self.context)
        return serializer.data


class CourseSerializer(CourseBriefSerializer):
    """
    ...
    """
    exercises = NestedHyperlinkedIdentityField(view_name='api:course-exercises-list', format='html')
    tree = NestedHyperlinkedIdentityField(view_name='api:course-tree-list', format='html')
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
    results_data = NestedHyperlinkedIdentityField(view_name='api:course-resultsdata-list')
    groups = NestedHyperlinkedIdentityField(view_name='api:course-groups-list')
    my_groups = NestedHyperlinkedIdentityField(view_name='api:course-mygroups-list')
    news = NestedHyperlinkedIdentityField(view_name='api:course-news-list')

    class Meta(CourseBriefSerializer.Meta):
        fields = (
            'language',
            'starting_time',
            'ending_time',
            'visible_to_students',
            # links
            'exercises',
            'tree',
            'points',
            'students',
            'taggings',
            'usertags',
            'my_points',
            'my_data',
            'data',
            'aggregate_data',
            'results_data',
            'groups',
            'my_groups',
            'news',
        )


class CourseWriteSerializer(AplusModelSerializer):
    """
    Serializer for creating and modifying course models using POST and PUT.
    """
    code = serializers.CharField()
    name = serializers.CharField()
    course_url = serializers.CharField()
    teachers = serializers.ListSerializer(child=serializers.CharField())

    class Meta(AplusModelSerializer.Meta):
        model = CourseInstance
        fields = (
            'code',
            'name',
            'course_url',
            'url',
            'instance_name',
            'language',
            'starting_time',
            'ending_time',
            'visible_to_students',
            'configure_url',
            'teachers',
        )

    def set_teachers(self, course: CourseInstance, teachers: list) -> None:
        users = []
        for i in teachers:
            userprofile: UserProfile = None
            try:
                user = User.objects.get(username=i)
            except User.DoesNotExist:
                # If user does not exist, create a new user.
                # If external authentication (e.g. Shibboleth) is used, other
                # attributes will be updated when user logs in for the first time.
                user = User.objects.create_user(i)

            userprofile = user.userprofile
            users.append(userprofile)

        course.set_teachers(users)

    def validate(self, data: OrderedDict) -> OrderedDict:
        # Take out fields that cannot be handled by standard serializer logic
        self.code = data.pop('code')
        self.name = data.pop('name')
        self.course_url = data.pop('course_url')
        self.teachers = data.pop('teachers')
        data = super().validate(data)
        return data

    def create(self, validated_data: OrderedDict) -> CourseInstance:
        course = Course.objects.filter(code=self.code).first()
        if not course:
            try:
                course = Course.objects.create(
                    code=self.code,
                    name=self.name,
                    url=self.course_url
                )
            except Exception as e:
                raise serializers.ValidationError(f"Course creation failed: {e}.")

        try:
            instance = CourseInstance.objects.create(**validated_data, course=course)
            self.set_teachers(instance, self.teachers)
            return instance

        except Exception as e:
            raise serializers.ValidationError(f"Course instance creation failed: {e}.")

    def update(self, instance: CourseInstance, validated_data: OrderedDict) -> CourseInstance:
        instance.url = validated_data.get('url', instance.url)
        instance.instance_name = validated_data.get('instance_name', instance.instance_name)
        instance.language = validated_data.get('language', instance.language)
        instance.starting_time = validated_data.get('starting_time', instance.starting_time)
        instance.ending_time = validated_data.get('ending_time', instance.ending_time)
        instance.visible_to_students = validated_data.get('visible_to_students', instance.visible_to_students)
        instance.configure_url = validated_data.get('configure_url', instance.configure_url)
        instance.save()
        self.set_teachers(instance, self.teachers)
        return instance

    def to_representation(self, instance: CourseInstance) -> OrderedDict:
        # Used for producing response to POST or PUT request.
        # Need to temporarily remove fields not present in CourseInstance,
        # otherwise the superclass to_representation call starts nagging
        for i in ['code', 'name', 'course_url']:
            self.fields.pop(i)
        resp = super(CourseWriteSerializer, self).to_representation(instance)
        resp['code'] = instance.course.code
        resp['name'] = instance.course.name
        resp['course_url'] = instance.course.url
        return resp

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


class TreeCourseModuleSerializer(serializers.Serializer):
    """
    Serializes items in the `modules` list of `CachedContent.data`. Does not
    derive from `AplusModelSerializer` because the items are `dict`s instead of
    model objects.
    """
    id = serializers.IntegerField()
    name = serializers.CharField()
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        serializer = TreeExerciseSerializer(
            instance=obj['children'],
            many=True,
            context=self.context
        )
        return serializer.data

class CourseNewsSerializer(CourseNewsBriefSerializer):

    class Meta(CourseNewsBriefSerializer.Meta):
        extra_kwargs = {
            'url': {
                'view_name': 'api:course-news-detail',
            }
        }
