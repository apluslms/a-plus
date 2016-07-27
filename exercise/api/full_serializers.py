from rest_framework import serializers
from rest_framework_extensions.fields import NestedHyperlinkedIdentityField

from userprofile.api.serializers import UserListField

from .serializers import (
    ExerciseBriefSerializer,
    SubmissionBriefSerializer,
)


__all__ = [
    'ExerciseSerializer',
    'SubmissionSerializer',
]


class ExerciseSerializer(ExerciseBriefSerializer):
    post_url = serializers.SerializerMethodField()
    submissions = NestedHyperlinkedIdentityField(
        view_name='api:exercise-submissions-list',
        lookup_map='exercise.api.views.ExerciseViewSet',
    )
    my_submissions = NestedHyperlinkedIdentityField(
        view_name='api:exercise-submissions-detail',
        lookup_map={
            'exercise_id': 'id',
            'user_id': lambda o=None: 'me',
        },
    )

    def get_post_url(self, obj):
        # FIXME: obj should implement .get_post_url() and that should be used here
        if obj.is_submittable:
            request = self.context['request']
            url = obj.get_url("exercise")
            return request.build_absolute_uri(url)
        return None

    class Meta(ExerciseBriefSerializer.Meta):
        fields = (
            'is_submittable',
            'post_url',
            'submissions',
            'my_submissions',
        )


class SubmissionSerializer(SubmissionBriefSerializer):
    #exercises = NestedHyperlinkedIdentityField(view_name='api:course-exercises-list', format='html')
    submitters = UserListField()
    #NestedHyperlinkedIdentityField(view_name='api:course-students-list', format='html')

    class Meta(SubmissionBriefSerializer.Meta):
        fields = (
            'html_url',
            #'exercise',
            'submitters',
            #'submission_data',
            #'is_submittable',
        )
