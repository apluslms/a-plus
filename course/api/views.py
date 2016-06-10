from rest_framework import generics, permissions, viewsets

from ..models import Course, CourseInstance
from .serializers import CourseSerializer, CourseInstanceSerializer

class CourseInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET list of course instances
    """
    queryset = CourseInstance.objects.all()
    serializer_class = CourseInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]
