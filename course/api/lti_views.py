import json
import logging
from typing import List

from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from .lti_serializers import LTILineItemSerializer, LTIScoresSerializer
from authorization.permissions import OAuth2TokenPermission, OAuth2ScopeChecker
from exercise.models import LTI1p3Exercise, Submission
from lib.api.constants import REGEX_INT
from userprofile.models import UserProfile


logger = logging.getLogger('aplus.course')


class CourseLineItemsViewSet(viewsets.ReadOnlyModelViewSet, OAuth2ScopeChecker):
    """
    ViewSet for reading LTI line items associated with a given course.
    Also implements 'scores' action for posting grades related to a line item.
    """
    parent_lookup_map = {'course_id': 'id'}
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    lookup_value_regex = REGEX_INT
    serializer_class = LTILineItemSerializer
    permission_classes = [OAuth2TokenPermission]
    pagination_class = None

    def check_token_scope(self, scopes: List[str]) -> bool:
        if self.action == 'scores':
            if 'https://purl.imsglobal.org/spec/lti-ags/scope/score' in scopes:
                return True
        else:
            if 'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly' in scopes:
                return True
        return False

    def get_queryset(self) -> QuerySet[LTI1p3Exercise]:
        return LTI1p3Exercise.objects.filter(course_module__course_instance__pk=self.kwargs['course_id'])

    @action(methods=['post'], detail=True, url_path='scores')
    def scores(self, request: Request, *args, **kwargs) -> Response:
        try:
            jsondata = json.loads(request.body)
        except ValueError:
            logger.error("LTI 1.3/scores: request body was not valid JSON")
            return Response('Not valid JSON', status=400)

        serializer = LTIScoresSerializer(data=jsondata)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        exercise = get_object_or_404(LTI1p3Exercise, pk=kwargs['id'])

        try:
            user = User.objects.get(pk=int(data.get('userId')))
        except UserProfile.DoesNotExist:
            logger.error("LTI 1.3/scores: User (%s) does not exist", data.get('userId'))
            return Response('UserProfile does not exist', status=400)
        except ValueError:
            logger.error("LTI 1.3/scores: Invalid user ID: %s", data.get('userId'))
            return Response('Invalid user ID', status=400)

        logger.info("Received LTI 1.3 'scores' request for exercise %s, user %s", str(exercise), str(user))
        sub = Submission.objects.filter(exercise=exercise, submitters=user.userprofile)
        if sub.exists():
            # When points come from LTI, we assume there is only one submission per exercise per user,
            # that can be updated if LTI delivers larger points than previously.
            # If points are not larger than previously, we will just ignore the message.
            # Some LTI tools seem to send scores updates quite frequently.
            sub = sub.first()
            adjusted = (1.0 * exercise.max_points * data.get('scoreGiven') / data.get('scoreMaximum'))
            if sub.grade >= adjusted:
                return Response({}, status=200)
        else:
            sub = Submission.objects.create(exercise=exercise)
            sub.submitters.set([user.userprofile])

        sub.set_points(data.get('scoreGiven'), data.get('scoreMaximum'))
        if data.get('gradingProgress') == 'FullyGraded':
            sub.set_ready()
        sub.grading_time = data.get('timestamp')
        sub.save()

        # Note: Moodle appears to expect 200 as response.
        # 204 (as shown in LTI spec example) is not acceptable for Moodle.
        return Response({}, status=200)
