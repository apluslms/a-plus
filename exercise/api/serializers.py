from rest_framework import serializers
from rest_framework.reverse import reverse

from lib.api.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import AplusModelSerializer, HtmlViewField
from userprofile.api.serializers import UserBriefSerializer
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
    #url = HtmlViewField()
    url = NestedHyperlinkedIdentityField(
        view_name='api:submission-files-detail',
        lookup_map='exercise.api.views.SubmissionFileViewSet',
    )

    class Meta(AplusModelSerializer.Meta):
        model = SubmittedFile
        fields = (
            'url',
            'filename',
            'param_name',
        )


class SubmitterStatsBriefSerializer(UserBriefSerializer):
    stats = serializers.SerializerMethodField()

    def get_stats(self, profile):
        return reverse(
            'api:exercise-submitter_stats-detail',
            kwargs={
                'exercise_id': self.context['view'].exercise.id,
                'user_id': profile.user.id,
            },
            request=self.context['request']
        )

    class Meta(UserBriefSerializer.Meta):
        fields = UserBriefSerializer.Meta.fields + (
            'stats',
        )
