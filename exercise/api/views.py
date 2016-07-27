from django.http import HttpResponse
from rest_framework import mixins, permissions, viewsets
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from lib.api.mixins import MeUserMixin
from lib.api.constants import REGEX_INT, REGEX_INT_ME

from ..models import (
    Submission,
    BaseExercise,
    SubmissionManager,
)
from .serializers import *
from .full_serializers import *


class ExerciseViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Url for GETting information about an exercise. (List of exercises can be
    fetched from /api/v2/courses/1/exercices)
    /api/v2/exercises/{exercise_id} (/api/v2/exercises/ does not actually exist)
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'exercise_id'
    lookup_value_regex = REGEX_INT
    serializer_class = ExerciseSerializer
    queryset = BaseExercise.objects.all()


class ExerciseSubmissionsViewSet(NestedViewSetMixin,
                                 MeUserMixin,
                                 mixins.ListModelMixin,
                                 viewsets.GenericViewSet):
    """
    * /api/v2/exercises/{exercise_id}/submissions
    * POST: Make a submission. Returns brief information about submission
    (including link to submission resource: /api/v2/exercises/{exercise_id}/
    submissions/{submissions_id})
    * GET: User can also get his old submission with GET.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = (TokenAuthentication,) # CSRF validation skipped
    lookup_url_kwarg = 'user_id'
    lookup_field = 'submitters__user__id'
    lookup_value_regex = REGEX_INT_ME
    parent_lookup_map = {
        'exercise_id': 'exercise.id',
    }
    serializer_class = SubmissionBriefSerializer
    queryset = Submission.objects.all()

    def filter_queryset(self, queryset):
        lookup_field = self.lookup_field
        lookup_url_kwarg = self.lookup_url_kwarg or lookup_field
        if lookup_url_kwarg in self.kwargs:
            filter_kwargs = {lookup_field: self.kwargs[lookup_url_kwarg]}
            queryset = queryset.filter(**filter_kwargs)
        return super(ExerciseSubmissionsViewSet, self).filter_queryset(queryset)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    # For POSTing a submission. An extra parameter exercise_id comes
    # from url. UNDER CONSTRUCTION!
    def create(self, request, exercise_id, version):
        # SubmissionManager.create_from_post(exercise, request.user, request)
        # Kts. myös a-plus/exercise/views.py rivi 99
        # First parse the request
        submitter = request.user.userprofile
        data = request.data
        print(data)
        print(exercise_id)
        print(submitter)

        # Before submission we need to check if user is able to make a submission
        try:
            exercice_to_submit = BaseExercise.objects.get(id=exercise_id)
        except BaseExercise.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        print(exercice_to_submit)

        if exercice_to_submit.is_submission_allowed([submitter]):
            print("Submission is available.")

            #serializer = SubmissionSerializer(data=request.data)
            #if serializer.is_valid():
            #    serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class SubmissionViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = 'submission_id'
    lookup_value_regex = REGEX_INT
    serializer_class = SubmissionSerializer
    queryset = Submission.objects.all()
