from collections import defaultdict

from course.models import LearningObjectCategory
from exercise.models import BaseExercise


class ScoreBoard(object):
    """
    Collects user score board data for template processing
    taking hidden categories into consideration.
    
    """    
    def __init__(self, course_instance, user=None):

        self.visible_categories = LearningObjectCategory.objects \
            .filter(course_instance=course_instance)
        if user and user.is_authenticated():
            self.visible_categories = self.visible_categories \
                .exclude(hidden_to=user.userprofile)

        self.visible_exercises = (BaseExercise.objects \
            .filter(course_module__course_instance=course_instance,
                    category__in=self.visible_categories)
            .select_related("course_module", "category") \
            .order_by("order"))

    def collect_tree(self, course_summary):
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
            {% for category, category_summary, categorized_exercise_level in category_level %}
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
    
        The CourseModule objects are ordered chronologically. The exercises are
        ordered by their order attribute. The order of the categories is
        determined by the order of the exercises. For example, if the first two
        exercises belong to category A and then the following two exercises
        belong to category B, our list of categories will begin like
        [A, B, ...]. Note that the category A may be in the list later too if
        there is more exercises that belong to the category A. For example, if
        the fifth exercises would belong to category A, our list of categories
        would be [A, B, A, ...].    
        """

        # Populate dictionary where unassigned keys return empty list.    
        visible_exercises_by_course_modules = defaultdict(list) 
        for exercise in self.visible_exercises:
            visible_exercises_by_course_modules[exercise.course_module] \
                .append(exercise)
    
        # Create sorted lists of dictionary items by module times.
        visible_exercises_by_course_modules = sorted(
            list(visible_exercises_by_course_modules.items()),
            key=lambda t: (t[0].closing_time, t[0].opening_time))
    
        # Create the tree structure.
        exercise_tree = [ (
            course_module,
            course_summary.get_module_summary(course_module),
            
            # Direct list of exercises.
            [ (
               exercise,
               course_summary.get_exercise_summary(exercise)
            ) for exercise in exercises],
    
            # Reservation for category groups.
            []
    
        ) for course_module, exercises in visible_exercises_by_course_modules]
    
        # Create category groups for each module.
        for course_module, _, exercises_and_summaries, category_group \
                in exercise_tree:
            for exercise, exercise_summary in exercises_and_summaries:
    
                # Create new category group if category changes. 
                if (len(category_group) == 0
                        or category_group[-1][0] != exercise.category):
                    category_group.append((
                        exercise.category,
                        course_summary.get_category_summary(exercise.category),
                        []
                    ))
                
                category_group[-1][2].append((exercise, exercise_summary))
    
        return exercise_tree

    def collect_categories(self, course_summary):
        return [course_summary.get_category_summary(category) \
                for category in self.visible_categories]
