from rest_framework import serializers

from ..models import LearningObject, Submission


class LearningObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObject
        fields = ('name', 'url', 'content', 'service_url')


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ('status', 'grade')
