import logging

from django import template

from apps.app_renderers import build_plugin_renderers
from course.models import CourseInstance
from exercise.exercise_models import BaseExercise
from exercise.submission_models import Submission


logger = logging.getLogger("aplus.apps")
register = template.Library()


@register.simple_tag
def plugin_renderers(user, some_model, view_name=None):
    """
    Builds the plugin renderers for a view.
    """
    profile = user.userprofile if user.is_authenticated else None
    if isinstance(some_model, CourseInstance):
        return build_plugin_renderers(
            some_model.plugins.all(),
            view_name or "course_instance",
            user_profile=profile,
            course_instance=some_model,
        )
    if isinstance(some_model, BaseExercise):
        course_instance = some_model.course_instance
        return build_plugin_renderers(
            course_instance.plugins.all(),
            view_name or "exercise",
            user_profile=profile,
            exercise=some_model,
            course_instance=course_instance,
        )
    if isinstance(some_model, Submission):
        course_instance = some_model.exercise.course_instance
        return build_plugin_renderers(
            course_instance.plugins.all(),
            view_name or "submission",
            user_profile=profile,
            submission=some_model,
            exercise=some_model.exercise,
            course_instance=course_instance,
        )
    # pylint: disable-next=logging-format-interpolation
    logger.warning("Unrecognized model type received for plugin_renderers tag: {}" \
                .format(str(type(some_model))))
    return []
