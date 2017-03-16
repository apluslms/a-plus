from rest_framework import serializers
from rest_framework.reverse import reverse
from course.api.serializers import CourseUsertagBriefSerializer
from lib.api.serializers import AlwaysListSerializer
from userprofile.api.serializers import UserBriefSerializer, UserListField
from ..cache.points import CachedPoints
from .full_serializers import SubmissionSerializer


class UserToTagSerializer(AlwaysListSerializer, CourseUsertagBriefSerializer):

    class Meta(CourseUsertagBriefSerializer.Meta):
        fields = CourseUsertagBriefSerializer.Meta.fields + (
            'name',
        )


class UserWithTagsSerializer(UserBriefSerializer):
    tags = serializers.SerializerMethodField()

    class Meta(UserBriefSerializer.Meta):
        fields = UserBriefSerializer.Meta.fields + (
            'tags',
        )

    def get_tags(self, obj):
        view = self.context['view']
        ser = UserToTagSerializer(
            obj.taggings.tags_for_instance(view.instance),
            context=self.context
        )
        return ser.data


class UserPointsSerializer(UserWithTagsSerializer):

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        view = self.context['view']
        points = CachedPoints(view.instance, obj.user, view.content)

        request = self.context['request']
        instance_id = view.instance.id

        def submission_url(submission_id):
            if submission_id is None:
                return None
            return reverse('api:submission-detail', kwargs={
                'submission_id': submission_id
            }, request=request)

        modules = []
        for module in points.modules_flatted():
            module_data = {}
            for key in [
                'id', 'name',
                'max_points', 'points_to_pass', 'submission_count',
                'points', 'points_by_difficulty', 'passed',
            ]:
                module_data[key] = module[key]

            exercises = []
            for entry in module['flatted']:
                if entry['type'] == 'exercise' and entry['submittable']:
                    exercise_data = {
                        'url': reverse('api:exercise-detail', kwargs={
                            'exercise_id': entry['id'],
                        }, request=request),
                        'best_submission': submission_url(entry['best_submission']),
                        'submissions': [submission_url(s['id']) for s in entry['submissions']],
                    }
                    for key in [
                        'id', 'name',
                        'max_points', 'points_to_pass', 'difficulty',
                        'submission_count', 'points', 'passed',
                    ]:
                        exercise_data[key] = entry[key]
                    exercises.append(exercise_data)

            module_data['exercises'] = exercises
            modules.append(module_data)

        total = points.total()
        for key in ['submission_count', 'points', 'points_by_difficulty']:
            rep[key] = total[key]
        rep['modules'] = modules

        return rep


class SubmissionDataSerializer(SubmissionSerializer):
    submitters = UserListField()
    submission_data = serializers.JSONField()
    grading_data = serializers.JSONField()

    class Meta(SubmissionSerializer.Meta):
        fields = (
            'late_penalty_applied',
            'submission_data',
            'grading_data',
        )
