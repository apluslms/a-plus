from rest_framework import serializers

from lib.api.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import (
    AlwaysListSerializer,
    AplusSerializerMeta,
    AplusModelSerializerBase,
    StatisticsSerializer,
)
from course.api.serializers import CourseBriefSerializer
from userprofile.api.serializers import UserBriefSerializer

from ..models import Submission
from .serializers import (
    ExerciseBriefSerializer,
    SubmissionBriefSerializer,
    SubmittedFileBriefSerializer,
)


__all__ = [
    'ExerciseSerializer',
    'ExerciseGraderSerializer',
    'SubmissionSerializer',
    'SubmissionGraderSerializer',
    'TreeExerciseSerializer',
    'ExerciseStatisticsSerializer',
]


class ExerciseSerializer(ExerciseBriefSerializer):
    course = CourseBriefSerializer(source='course_instance')
    post_url = serializers.SerializerMethodField()
    exercise_info = serializers.JSONField()
    submissions = NestedHyperlinkedIdentityField(
        view_name='api:exercise-submissions-list',
        lookup_map='exercise.api.views.ExerciseViewSet',
    )
    my_submissions = NestedHyperlinkedIdentityField(
        view_name='api:exercise-submissions-detail',
        lookup_map={
            'exercise_id': 'id',
            'user_id': lambda o=None: 'me',
        },
    )
    my_stats = NestedHyperlinkedIdentityField(
        view_name='api:exercise-submitter_stats-detail',
        lookup_map={
            'exercise_id': 'id',
            'user_id': lambda o=None: 'me',
        },
    )
    statistics = NestedHyperlinkedIdentityField(view_name='exercise-statistics')

    def get_post_url(self, obj):
        # FIXME: obj should implement .get_post_url() and that should be used here
        if obj.is_submittable:
            request = self.context['request']
            url = obj.get_url("exercise")
            return request.build_absolute_uri(url)
        return None

    class Meta(ExerciseBriefSerializer.Meta):
        fields = (
            'name',
            'course',
            'is_submittable',
            'post_url',
            'exercise_info',
            'templates',
            'submissions',
            'my_submissions',
            'my_stats',
            'statistics',
        )


class ExerciseGraderSerializer(AplusModelSerializerBase):
    url = NestedHyperlinkedIdentityField(
        view_name='api:exercise-grader',
        lookup_map='exercise.api.views.ExerciseViewSet',
    )
    exercise = ExerciseBriefSerializer(source='*')

    class Meta(AplusSerializerMeta):
        model = Submission
        fields = (
            'url',
            'exercise',
        )


class SubmitterLinks(AlwaysListSerializer, UserBriefSerializer):
    pass


class SubmittedFileLinks(AlwaysListSerializer, SubmittedFileBriefSerializer):
    pass


class SubmissionSerializer(SubmissionBriefSerializer):
    exercise = ExerciseBriefSerializer()
    submitters = SubmitterLinks()
    submission_data = serializers.JSONField()
    files = SubmittedFileLinks()
    grade = serializers.SerializerMethodField()
    grader = UserBriefSerializer()
    feedback = serializers.SerializerMethodField()
    assistant_feedback = serializers.SerializerMethodField()
    grading_data = serializers.SerializerMethodField()

    class Meta(SubmissionBriefSerializer.Meta):
        fields = (
            'html_url',
            'exercise',
            'submitters',
            'submission_data',
            'files',
            'status',
            'grade',
            'late_penalty_applied',
            'grading_time',
            'grader',
            'feedback',
            'assistant_feedback',
            'grading_data',
        )

    def get_grade(self, obj):
        return obj.grade if self.context['view'].feedback_revealed else 0

    def get_feedback(self, obj):
        return obj.feedback if self.context['view'].feedback_revealed else None

    def get_assistant_feedback(self, obj):
        return obj.assistant_feedback if self.context['view'].feedback_revealed else None

    def get_grading_data(self, obj):
        return obj.grading_data if self.context['view'].feedback_revealed else None


class SubmissionInGraderSerializer(SubmissionBriefSerializer):
    class Meta(SubmissionBriefSerializer.Meta):
        fields = (
            'html_url',
        )


class SubmissionGraderSerializer(AplusModelSerializerBase):
    url = NestedHyperlinkedIdentityField(
        view_name='api:submission-grader',
        lookup_map='exercise.api.views.SubmissionViewSet',
    )
    submission = SubmissionInGraderSerializer(source='*')
    exercise = ExerciseBriefSerializer()

    class Meta(AplusSerializerMeta):
        model = Submission
        fields = (
            'url',
            'submission',
            'exercise',
            'grading_data',
            'is_graded',
        )


class TreeExerciseSerializer(serializers.Serializer):
    """
    Serializes items in the `children` lists found in the `CachedContent.data`
    data structure. Does not derive from `AplusModelSerializer` because the
    items are `dict`s instead of model objects.
    """
    id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.SerializerMethodField()
    url = NestedHyperlinkedIdentityField(
        view_name='api:exercise-detail',
        lookup_map={'exercise_id': 'id'},
    )
    children = serializers.SerializerMethodField()

    def get_type(self, obj):
        return 'exercise' if obj['submittable'] else 'chapter'

    def get_children(self, obj):
        serializer = TreeExerciseSerializer(
            instance=obj['children'],
            many=True,
            context=self.context
        )
        return serializer.data


class ExerciseStatisticsSerializer(StatisticsSerializer):
    exercise_id = serializers.IntegerField(read_only=True)
