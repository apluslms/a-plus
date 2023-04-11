from rest_framework import filters, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.settings import api_settings

from lib.api.filters import FieldValuesFilter
from lib.api.mixins import ListSerializerMixin, MeUserMixin
from lib.api.constants import REGEX_INT_ME

from ..models import UserProfile
from ..permissions import IsTeacherOrAdminOrSelf
from .serializers import UserBriefSerializer
from .full_serializers import UserSerializer


class UserViewSet(ListSerializerMixin,
                  MeUserMixin,
                  viewsets.ReadOnlyModelViewSet):
    """
    The `users` endpoint returns information about all users.

    Operations
    ----------

    `GET /users/`:
        returns a list of all users.

    `GET /users/<user_id>/`:
        returns the details of a specific user.

    `GET /users/me/`:
        returns the details of the current user.
    """
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsTeacherOrAdminOrSelf,
    ]
    filter_backends = (
        IsTeacherOrAdminOrSelf,
        filters.SearchFilter,
        FieldValuesFilter,
    )
    search_fields = ['user__first_name', 'user__last_name', 'student_id', 'user__email']
    field_values_map = {'id': 'user_id', 'student_id': 'student_id', 'email': 'user__email'}
    lookup_field = 'user_id' # UserProfile.user.id
    lookup_url_kwarg = 'user_id'
    lookup_value_regex = REGEX_INT_ME
    listserializer_class = UserBriefSerializer
    serializer_class = UserSerializer
    queryset = UserProfile.objects.all()

    # if update is required, change to normal modelviewset and
    # change permissions


class MeDetail(APIView):
    """
    The `me` endpoint returns information about the current user.

    Operations
    ----------

    `GET /me/`:
        returns the details of the current user.
    """
    def get(self, request, version, format=None): # pylint: disable=unused-argument redefined-builtin
        userinstance = self.request.user.userprofile

        serializer = UserSerializer(userinstance, context={
                        'request': request,
                        })
        return Response(serializer.data)
