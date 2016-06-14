from rest_framework import serializers

from ..models import LearningObject, Submission, BaseExercise

# LearningObject is base of exercises.
class LearningObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObject
        fields = ('name', 'course_module', 'url', 'content', 'service_url', 'objects')

# Between Submission and LearningObject is BaseExercise which actually is
# THE base of all exercises. BaseExercise is inherited from LearningObject.
class BaseExerciseSerializer(serializers.ModelSerializer):
    model = BaseExercise
    fields = ('')

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        # Exercise is foreignkey to BaseExercise
        fields = ('exercise', 'feedback', 'grade', 'status', 'grade')
