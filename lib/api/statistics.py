from datetime import timedelta

from rest_framework import generics
from django.db.models import QuerySet
from django.utils import timezone

from exercise.submission_models import Submission
from .serializers import StatisticsSerializer


class BaseStatisticsView(generics.RetrieveAPIView):
    """
    Returns submission statistics for the entire system, over a given time window.

    Returns the following attributes:

    - `submission_count`: total number of submissions.
    - `submitters`: number of users submitting.

    Operations
    ----------

    `GET /statistics/`:
        returns the statistics for the system.

    - URL parameters:
        - `endtime`: date and time in ISO 8601 format indicating the end point
          of time window we are interested in. Default: now.
        - `starttime`: date and time in ISO 8601 format indicating the start point
          of time window we are interested in. Default: one day before endtime
    """
    serializer_class = StatisticsSerializer

    def get_queryset(self) -> QuerySet:
        queryset = Submission.objects.all()

        endtime = self.request.query_params.get('endtime')
        starttime = self.request.query_params.get('starttime')
        serializer = self.get_serializer(data={'starttime': starttime, 'endtime': endtime})
        serializer.is_valid(raise_exception=True)
        self.endtime = serializer.validated_data['endtime'] or timezone.now()
        self.starttime = serializer.validated_data['starttime'] or self.endtime - timedelta(days=1)

        return queryset.filter(submission_time__range=[self.starttime, self.endtime])

    def get_object(self):
        qs = self.get_queryset()
        obj = {
            'starttime': self.starttime,
            'endtime': self.endtime,
            'submission_count': qs.count(),
            'submitters': qs.values('submitters').distinct().count()
        }
        return obj
