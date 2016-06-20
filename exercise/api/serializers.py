from rest_framework import serializers
from lib.api import HtmlViewField
from ..models import LearningObject, Submission, BaseExercise

# LearningObject is base of exercises.
class LearningObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObject
        fields = ('name', 'course_module', 'url', 'content', 'service_url', 'objects')

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        # Exercise is foreignkey to BaseExercise
        fields = ('exercise', 'submitters', 'submission_data')
