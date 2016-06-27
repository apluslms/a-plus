from rest_framework import permissions, viewsets
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.renderers import JSONRenderer

from lib.api import ListSerializerMixin

from lib.api import ListSerializerMixin

from ..models import UserProfile
from .serializers import \
    UserSerializer, UserBriefSerialiser


class UserViewSet(ListSerializerMixin, viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user_id'
    listserializer_class = UserBriefSerialiser
    serializer_class = UserSerializer

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
