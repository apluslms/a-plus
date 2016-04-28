from exercise.models import LearningObject
from exercise.models import Submission
from exercise.models import BaseExercise
from exercise.serializers import LearningObjectSerializer
from exercise.serializers import SubmissionSerializer
from rest_framework import generics
from rest_framework import permissions


class LearningObjectList(generics.ListAPIView):
    """
    GET list of exercises
    """
    queryset = LearningObject.objects.all()
    serializer_class = LearningObjectSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class SubmissionList(generics.ListCreateAPIView):
    """
    * GET/POST a submission
    * GET is for getting the result of SubmissionDetail
    * POST is for making new SubmissionDetail
    """
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    # Override the POST-method
    def perform_create(self, serializer):
        # First parse the request
        submitter = self.request.user
        data = self.request.data
        print(data)
        exercise_name = data["exercise_name"]

        # Before submission we need to check if user is able to make a submission
        try:
            exercice_to_submit = BaseExercise.objects.get(name=exercise_name)
        except DoesNotExist:
            return Response(status=404)

        print(exercice_to_submit)
        if exercice_to_submit.is_submission_allowed(students):
            print("Submission is available.")
        else:
            return Response(status=404)
