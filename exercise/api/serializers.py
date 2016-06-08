from rest_framework import serializers

from ..models import LearningObject, Submission


class LearningObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObject
        fields = ('name', 'course_module', 'url', 'content', 'service_url', 'objects')


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ('exercise', 'feedback', 'grade', 'status', 'grade')
