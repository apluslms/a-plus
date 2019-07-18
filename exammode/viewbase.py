from lib.viewbase import BaseMixin, BaseTemplateView

from .models import ExamSession, ExamAttempt


class ExamStarMixin(BaseMixin):

    def get_resource_objects(self):
        super().get_resource_objects()
        course_instance =
