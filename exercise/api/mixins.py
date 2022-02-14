from django.http import Http404

from authorization.api.mixins import ApiResourceMixin
from authorization.permissions import ACCESS
from course.viewbase import (
    CourseInstanceBaseMixin,
    CourseModuleBaseMixin,
)
from ..models import (
    LearningObject,
    Submission,
)
from ..viewbase import (
    ExerciseBaseMixin,
    ExerciseRevealRuleMixin,
    SubmissionBaseMixin,
)


class ExerciseBaseResourceMixin(ExerciseRevealRuleMixin,
                                CourseInstanceBaseMixin,
                                CourseModuleBaseMixin,
                                ExerciseBaseMixin):
    exercise_kw = 'exercise_id'

    def get_exercise_object(self):
        exercise = self.get_object_or_none(self.exercise_kw, LearningObject)
        if not exercise:
            raise Http404("Learning object not found")
        return exercise

    def get_course_module_object(self):
        return self.exercise.course_module

    def get_course_instance_object(self):
        return self.module.course_instance


class ExerciseResourceMixin(ExerciseBaseResourceMixin, ApiResourceMixin):
    access_mode = ACCESS.ANONYMOUS # not really used, see get_access_mode() below

    def get_access_mode(self):
        # This method is defined here because some permissions expect view classes
        # to have this method. Access mode was not really intended to be used by
        # the API, though. Class CourseInstanceBaseMixin actually defines this
        # method, but it calls super(), which would crash unless this class
        # defined this method.
        return self.access_mode


class SubmissionBaseResourceMixin(ExerciseBaseResourceMixin,
                                  SubmissionBaseMixin):
    submission_kw = 'submission_id'

    def get_submission_object(self):
        submission = self.get_object_or_none(self.submission_kw, Submission)
        if not submission:
            raise Http404("Submission not found")
        return submission

    def get_exercise_object(self):
        return self.submission.exercise


class SubmissionResourceMixin(SubmissionBaseResourceMixin, ApiResourceMixin):
    access_mode = ACCESS.ANONYMOUS # not really used, see get_access_mode() below

    def get_access_mode(self):
        # This method is defined here because some permissions expect view classes
        # to have this method. Access mode was not really intended to be used by
        # the API, though. Class CourseInstanceBaseMixin actually defines this
        # method, but it calls super(), which would crash unless this class
        # defined this method.
        return self.access_mode
