from typing import Type, TypeVar

from django.db.models import Model
from django.http import Http404

from authorization.api.mixins import ApiResourceMixin
from authorization.permissions import ACCESS
from course.models import CourseInstance, CourseModule
from course.viewbase import (
    CourseInstanceBaseMixin,
    CourseModuleBaseMixin,
)
from lib.helpers import object_at_runtime
from ..models import (
    LearningObject,
    Submission,
)
from ..viewbase import (
    ExerciseBaseMixin,
    SubmissionBaseMixin,
)


@object_at_runtime
class _ExerciseBaseResourceMixinBase:
    TModel = TypeVar('TModel', bound=Model)
    def get_object_or_none(self, kwarg: str, model: Type[TModel]) -> TModel: ...


class ExerciseBaseResourceMixin(CourseInstanceBaseMixin,
                                CourseModuleBaseMixin,
                                ExerciseBaseMixin,
                                _ExerciseBaseResourceMixinBase):
    exercise_kw = 'exercise_id'

    def get_exercise_object(self) -> LearningObject:
        exercise = self.get_object_or_none(self.exercise_kw, LearningObject)
        if not exercise:
            raise Http404("Learning object not found")
        return exercise.as_leaf_class()

    def get_course_module_object(self) -> CourseModule:
        return self.exercise.course_module

    def get_course_instance_object(self) -> CourseInstance:
        return self.module.course_instance


class ExerciseResourceMixin(ExerciseBaseResourceMixin, ApiResourceMixin):
    access_mode = ACCESS.ANONYMOUS # not really used, see get_access_mode() below

    def get_access_mode(self) -> int:
        # This method is defined here because some permissions expect view classes
        # to have this method. Access mode was not really intended to be used by
        # the API, though. Class CourseInstanceBaseMixin actually defines this
        # method, but it calls super(), which would crash unless this class
        # defined this method.
        return self.access_mode


class SubmissionBaseResourceMixin(ExerciseBaseResourceMixin,
                                  SubmissionBaseMixin):
    submission_kw = 'submission_id'

    def get_submission_object(self) -> Submission:
        submission = self.get_object_or_none(self.submission_kw, Submission)
        if not submission:
            raise Http404("Submission not found")
        return submission

    def get_exercise_object(self) -> LearningObject:
        return self.submission.exercise


class SubmissionResourceMixin(SubmissionBaseResourceMixin, ApiResourceMixin):
    access_mode = ACCESS.ANONYMOUS # not really used, see get_access_mode() below

    def get_access_mode(self) -> int:
        # This method is defined here because some permissions expect view classes
        # to have this method. Access mode was not really intended to be used by
        # the API, though. Class CourseInstanceBaseMixin actually defines this
        # method, but it calls super(), which would crash unless this class
        # defined this method.
        return self.access_mode
