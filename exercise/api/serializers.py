from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework_extensions.fields import NestedHyperlinkedIdentityField

from lib.api.serializers import AplusModelSerializer, HtmlViewField
from userprofile.api.serializers import UserBriefBaseSerializer
from ..models import Submission, SubmittedFile, BaseExercise


__all__ = [
    'ExerciseBriefSerializer',
    'SubmissionBriefSerializer',
    'SubmittedFileBriefSerializer',
    'SubmitterStatsBriefSerializer',
]


class ExerciseBriefSerializer(AplusModelSerializer):
    url = NestedHyperlinkedIdentityField(
        view_name='api:exercise-detail',
        lookup_map='exercise.api.views.ExerciseViewSet',
    )
    display_name = serializers.CharField(source='__str__')

    class Meta(AplusModelSerializer.Meta):
        model = BaseExercise
        fields = (
            'url',
            'html_url',
            'display_name',
        )


class SubmissionBriefSerializer(AplusModelSerializer):
    #display_name = serializers.CharField(source='__str__')

    class Meta(AplusModelSerializer.Meta):
        model = Submission
        fields = (
            'submission_time',
        )
        extra_kwargs = {
            'url': {
                'view_name': 'api:submission-detail',
                'lookup_map': 'exercise.api.views.SubmissionViewSet',
            }
        }


class SubmittedFileBriefSerializer(AplusModelSerializer):
    url = HtmlViewField()

    class Meta(AplusModelSerializer.Meta):
        model = SubmittedFile
        fields = (
            'url',
            'filename',
            'param_name',
        )


class SubmitterStatsBriefSerializer(UserBriefBaseSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return reverse('api:exercise-submitter_stats-detail', kwargs={
            'exercise_id': self.context['view'].exercise.id,
            'user_id': obj.user.id,
        }, request=self.context['request'])
