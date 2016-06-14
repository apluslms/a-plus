from rest_framework import generics, permissions, viewsets

from ..models import LearningObject, Submission, BaseExercise, SubmissionManager
from .serializers import *

class LearningObjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET list of learning objects or one object
    """
    queryset = LearningObject.objects.all()
    serializer_class = LearningObjectSerializer
    permission_classes = [permissions.IsAuthenticated]

class ExerciseViewSet(viewsets.ModelViewSet):
    """
    GET: List exercises (/exercises)
    GET: Get one exercise (/exercises/123)
    POST: Make a submission (/exercises/123/submissions)
    GET: Get a result of a submission (/exercises/123/submissions/1)
    """
    queryset = BaseExercise.objects.all()
    serializer_class = BaseExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]

    # For POSTing a submission. An extra parameter exercise_id comes
    # from url
    def create(self, request):

        #SubmissionManager.create_from_post(exercise, request.user, request)
        # Kts. myös a-plus/exercise/views.py rivi 99
        # First parse the request
        print(exercise_id)
        """
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
            return Response(status=404)"""

    # For GETting a result of submission
    def retrieve(self, request, pk=None):
        print(pk)

class SubmissionViewSet(viewsets.ModelViewSet):
    """
    GET list of submissions to related exercise
    GET result of a submission
    POST make a new submission to related exercise
    """
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
