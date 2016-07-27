from rest_framework import serializers
from rest_framework_extensions.fields import NestedHyperlinkedIdentityField
from lib.api.serializers import AplusModelSerializer

from ..models import Submission, BaseExercise


__all__ = [
    'ExerciseBriefSerializer',
    'SubmissionBriefSerializer',
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
        #fields = (
        #    'display_name',
        #)
        extra_kwargs = {
            'url': {
                'view_name': 'api:submission-detail',
                'lookup_map': 'exercise.api.views.SubmissionViewSet',
            }
        }
