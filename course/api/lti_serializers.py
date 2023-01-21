from rest_framework import serializers
from rest_framework.reverse import reverse

from exercise.models import LTI1p3Exercise


class LTILineItemSerializer(serializers.Serializer):
    """
    Serializer for LTI line item.
    See LTI Assignments and Grades specification, section 3.2.
    """
    # Disabling linter warnings for mixedCase (N815) because the names come from LTI spec.
    id = serializers.SerializerMethodField()
    scoreMaximum = serializers.IntegerField(source='max_points') # noqa: N815
    label = serializers.CharField(source="__str__")
    startDateTime = serializers.DateTimeField(source='course_module.opening_time', allow_null=True) # noqa: N815
    endDateTime = serializers.DateTimeField(source='course_module.closing_time', allow_null=True) # noqa: N815
    resourceLinkId = serializers.CharField(source='get_resource_link_id', allow_null=True) # noqa: N815

    def get_id(self, obj: LTI1p3Exercise) -> str:
        return reverse(
            'api:course-lineitems-detail',
            kwargs={ 'course_id' : str(obj.course_module.course_instance.pk), 'id' : str(obj.pk) },
            request=self.context['request'],
        )


class LTIScoresSerializer(serializers.Serializer):
    """
    Serializer for LTI 'scores' message associated with a line item.
    See LTI Assignments and Grades specification, section 3.4.
    """
    # Disabling linter warnings for mixedCase (N815) because the names come from LTI spec.
    timestamp = serializers.DateTimeField()
    scoreGiven = serializers.FloatField() # noqa: N815
    scoreMaximum = serializers.FloatField() # noqa: N815
    activityProgress = serializers.CharField() # noqa: N815
    gradingProgress = serializers.CharField() # noqa: N815
    userId = serializers.CharField() # noqa: N815
