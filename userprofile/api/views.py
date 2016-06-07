from rest_framework import generics, permissions, viewsets

from ..models import UserProfile
from .serializers import UserSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    # if update is required, change to normal modelviewset and
    # change permissions