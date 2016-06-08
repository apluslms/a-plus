from rest_framework import generics, permissions, viewsets

from ..models import LearningObject, Submission, BaseExercise, SubmissionManager
from .serializers import LearningObjectSerializer, SubmissionSerializer

class LearningObjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET list of learning objects or one object
    """
    queryset = LearningObject.objects.all()
    serializer_class = LearningObjectSerializer
    permission_classes = [permissions.IsAuthenticated]

class SubmissionViewSet(viewsets.ModelViewSet):
    """
    POST a submission
    GET a result of submission
    """
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    # For POSTing a submission. An extra parameter exercise_id comes
    # from url
    def create(self, request, exercise_id):

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



# TODO: Under construction
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
