from collections import defaultdict

from course.models import LearningObjectCategory
from exercise.models import BaseExercise


def collect_tree(course_summary):
    """
    Creates a special data structure from course summary for template
    usage in a way that makes the template as simple as possible.

    This is how the structure should be used in the template:

    {% for course_module, round_summary, uncategorized_exercise_level, category_level in exercise_tree %}
        ...
        {% for exercise, exercise_summary in uncategorized_exercise_level %}
            ... <exercise icon list> ...
        {% endfor %}
        ...
        {% for category, categorized_exercise_level in category_level %}
            ...
            {% for exercise, exercise_summary in categorized_exercise_level %}
                ... <exercises inside categories> ...
            {% endfor %}
            ...
        {% endfor %}
        ...
    {% endfor %}

    Notice that all the nodes of the tree are tuples (all the lists contain
    tuples). The tuples are of course formatted the same way in a
    particular tree level (list).

    The order of the categories is determined by the order of the exercises.
    For example, if the first two exercises belong to category A and then the
    following two exercises belong to category B, our list of categories will
    begin like [A, B, ...]. Note that the category A may be in the list later
    too if there is more exercises that belong to the category A. For example,
    if the fifth exercises would belong to category A, our list of categories
    would be [A, B, A, ...].
    """
    exercise_tree = [ (
        module_summary.module,
        module_summary,

        # Direct list of exercises.
        [ (
           exercise_summary.exercise,
           exercise_summary
        ) for exercise_summary in module_summary.exercise_summaries
            if exercise_summary.exercise.status != 'hidden'],

        # Reservation for category groups.
        []

    ) for module_summary in course_summary.module_summaries
        if module_summary.module.status != 'hidden']

    # Create category groups for each module.
    for course_module, _, exercises_and_summaries, category_group \
            in exercise_tree:
        for exercise, exercise_summary in exercises_and_summaries:

            # Create new category group if category changes.
            if (len(category_group) == 0
                    or category_group[-1][0] != exercise.category):
                category_group.append((
                    exercise.category,
                    []
                ))

            category_group[-1][1].append((exercise, exercise_summary))

    return exercise_tree
