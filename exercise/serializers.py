from exercise.exercise_models import LearningObject
from exercise.submission_models import Submission
from rest_framework import serializers


class LearningObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObject
        fields = ('name', 'url', 'content', 'service_url')


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ('status', 'grade')
