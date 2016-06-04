from userprofile.models import UserProfile
from userprofile.serializers import UserPSerializer
from rest_framework import generics
from rest_framework import permissions


class UserList(generics.ListCreateAPIView):
    """
    GET/POST to list of users
    GET is for everyone and POSTer needs to be authenticated
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserPSerializer

    # Overwrite the default value. This makes GET available for everyone
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

# TODO: Under construction
class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE to single user
    GET is for everyone and others need to be authenticated
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserPSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    # Allow only superuser to put/patch/delete, so override those
    # methods
    def perform_update(self, serializer):
        submitter = self.request.user
        data = self.request.data
        print(submitter)
        print(data)
