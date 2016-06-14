from rest_framework import permissions, viewsets
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.renderers import JSONRenderer

from ..models import UserProfile
from .serializers import UserSerializer
from course.models import CourseInstance

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user_id'

    # if update is required, change to normal modelviewset and
    # change permissions

class MeDetail(APIView):
    def get(self, request, version, format=None):
        username = self.request.user
        userinstance = UserProfile.objects.get(user=username)

        serializer = UserSerializer(userinstance, context={
                        'request': request,
                        })
        return Response(serializer.data)
