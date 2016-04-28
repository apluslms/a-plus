from rest_framework import generics, permissions

from ..models import LearningObject, Submission, BaseExercise
from .serializers import LearningObjectSerializer, SubmissionSerializer


class LearningObjectList(generics.ListAPIView):
    """
    GET list of exercises
    """
    queryset = LearningObject.objects.all()
    serializer_class = LearningObjectSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

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
