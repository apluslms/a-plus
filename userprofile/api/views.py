from rest_framework import permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.settings import api_settings

from lib.api.mixins import ListSerializerMixin, MeUserMixin
from lib.api.constants import REGEX_INT_ME

from ..models import UserProfile
from ..permissions import IsAdminOrUserObjIsSelf
from .serializers import *
from .full_serializers import *


class UserViewSet(ListSerializerMixin,
                  MeUserMixin,
                  viewsets.ReadOnlyModelViewSet):
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [
        IsAdminOrUserObjIsSelf,
    ]
    filter_backends = (
        IsAdminOrUserObjIsSelf,
    )
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
    Url for checking that student has given correct arguments for plugin and
    GETting student information such as student id, enrolled course, /api/v2/me
    """
    def get(self, request, version, format=None):
        userinstance = self.request.user.userprofile

        serializer = UserSerializer(userinstance, context={
                        'request': request,
                        })
        return Response(serializer.data)
