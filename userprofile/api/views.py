from rest_framework import generics, permissions, viewsets

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