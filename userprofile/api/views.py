from rest_framework import permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from lib.api import ListSerializerMixin

from ..models import UserProfile
from .serializers import *


class UserViewSet(ListSerializerMixin,
                  viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user_id'
    listserializer_class = UserBriefSerialiser
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
