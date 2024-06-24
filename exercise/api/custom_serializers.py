from typing import Any, Dict, Optional

from rest_framework import serializers
from rest_framework.reverse import reverse

from course.api.serializers import CourseUsertagBriefSerializer
from course.models import Enrollment
from lib.api.serializers import AlwaysListSerializer
from userprofile.api.serializers import UserBriefSerializer
from userprofile.models import UserProfile
from ..cache.points import CachedPoints, ExercisePoints, SubmissionEntry


class UserToTagSerializer(AlwaysListSerializer, CourseUsertagBriefSerializer):

    class Meta(CourseUsertagBriefSerializer.Meta):
        fields = CourseUsertagBriefSerializer.Meta.fields + (
            'name',
        )


class UserWithTagsSerializer(UserBriefSerializer):
    tags = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta(UserBriefSerializer.Meta):
        fields = UserBriefSerializer.Meta.fields + (
            'tags',
            'role',
        )

    def get_tags(self, obj):
        view = self.context['view']
        ser = UserToTagSerializer(
            obj.taggings.tags_for_instance(view.instance),
            context=self.context
        )
        return ser.data

    def get_role(self, obj):
        view = self.context['view']
        try:
            enrollment = Enrollment.objects.get(
                course_instance=view.instance,
                user_profile=obj
            )
            return Enrollment.ENROLLMENT_ROLE[enrollment.role]
        except Enrollment.DoesNotExist:
            return ""


class ExercisePointsSerializer(serializers.Serializer):

    def to_representation(self, entry: ExercisePoints) -> Dict[str, Any]: # pylint: disable=arguments-renamed
        request = self.context['request']

        def exercise_url(exercise_id: int) -> str:
            return reverse('api:exercise-detail', kwargs={
                'exercise_id': exercise_id,
            }, request=request)

        def submission_url(submission: Optional[SubmissionEntry]) -> Optional[str]:
            if submission is None:
                return None
            return reverse('api:submission-detail', kwargs={
                'submission_id': submission.id
            }, request=request)

        def submission_obj(submission_cached: SubmissionEntry) -> Dict[str, Any]:
            return {
                'id': submission_cached.id,
                'url': submission_url(submission_cached),
                'submission_time': submission_cached.date,
                'grade': submission_cached.points,
            }

        submissions = [submission_obj(s) for s in entry.submissions]
        exercise_data = {
            'url': exercise_url(entry.id),
            'best_submission': submission_url(entry.best_submission),
            'submissions': [s["url"] for s in submissions],
            'submissions_with_points': submissions,
        }
        for key in [
            # exercise
            'id',
            'name',
            'difficulty',
            'max_points',
            'points_to_pass',
            'submission_count',
            # best submission
            'points',
            'passed',
            # 'official',
        ]:
            exercise_data[key] = getattr(entry, key)
        exercise_data['official'] = (entry.graded and
                                     not entry.unconfirmed)
        return exercise_data


class UserPointsSerializer(UserWithTagsSerializer):

    def to_representation(self, obj: UserProfile) -> Dict[str, Any]: # pylint: disable=arguments-renamed
        rep = super().to_representation(obj)
        view = self.context['view']
        points = CachedPoints(view.instance, obj.user, view.is_course_staff)
        modules = []
        for module in points.modules_flatted():
            module_data = {}
            for key in [
                'id', 'name',
                'max_points', 'points_to_pass', 'submission_count',
                'points', 'points_by_difficulty', 'passed',
            ]:
                module_data[key] = getattr(module, key)

            exercises = []
            for entry in module.flatted:
                if isinstance(entry, ExercisePoints):
                    exercises.append(
                        ExercisePointsSerializer(entry, context=self.context).data
                    )
            module_data['exercises'] = exercises
            modules.append(module_data)

        total = points.total()
        for key in [
            'max_points', 'max_points_by_difficulty', 'submission_count',
            'points', 'points_by_difficulty',
        ]:
            rep[key] = getattr(total, key)
        rep['modules'] = modules

        return rep


class SubmitterStatsSerializer(UserWithTagsSerializer):

    def to_representation(self, obj: UserProfile) -> Dict[str, Any]: # pylint: disable=arguments-renamed
        rep = super().to_representation(obj)
        view = self.context['view']
        entry = ExercisePoints.get(view.exercise, obj.user, view.is_course_staff)
        data = ExercisePointsSerializer(entry, context=self.context).data
        for key,value in data.items():
            rep[key] = value
        return rep
