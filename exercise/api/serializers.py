from rest_framework import serializers
from lib.api.serializers import HtmlViewField
from ..models import LearningObject, Submission, BaseExercise


__all__ = [
    'LearningObjectSerializer',
    'SubmissionSerializer',
]


# LearningObject is base of exercises.
class LearningObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObject
        fields = ('name', 'course_module', 'url', 'content', 'service_url', 'objects')

class SubmissionSerializer(serializers.HyperlinkedModelSerializer):
    html_url = HtmlViewField()
    display_name = serializers.CharField(source='__str__')

    class Meta:
        model = Submission
        fields = (
            'html_url',
            'exercise',
            'submitters',
            'submission_data',
            'display_name',
            'is_submittable',
        )
