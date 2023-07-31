from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max

from .cache.content import CachedContent
from .models import BaseExercise, Submission


class ResultTable:
    """
    WARNING: Constructing this class is a heavy database operation.

    Models the table displaying the grades for each student on each exercise.
    Result tables are generated dynamically when needed and not stored
    in a database.
    """

    def __init__(self, course_instance):
        """
        Instantiates a new ResultTable for the given course instance.
        After initialization the table is filled with grades from the database.
        """
        self.course_instance = course_instance

        # Exercises on the course.
        self.exercises = list(self.__get_exercises())
        self.categories = course_instance.categories.all()

        # Students on the course.
        self.students = list(course_instance.get_student_profiles())

        # Empty results table.
        self.results = {
            student.id: {
                exercise.id: None for exercise in self.exercises
            } for student in self.students
        }
        self.results_by_category = {
            student.id: {
                category.id: 0 for category in self.categories
            } for student in self.students
        }

        # Fill the results with the data from the database.
        self.__collect_student_grades()


    def __get_exercises(self):
        def get_descendant_ids(children):
            for child in children:
                if child.children:
                    yield from get_descendant_ids(child.children)
                else:
                    yield child.id

        content = CachedContent(self.course_instance)
        for id in get_descendant_ids(content.modules()): # pylint: disable=redefined-builtin
            try:
                yield BaseExercise.objects.get(learningobject_ptr_id=id)
            except ObjectDoesNotExist:
                continue


    def __collect_student_grades(self):
        """
        Helper for the __init__.
        This method puts the data from the database in to the results table.
        """
        submissions = list(Submission.objects \
            .filter(
                exercise__course_module__course_instance=self.course_instance,
                status=Submission.STATUS.READY
            ).values("submitters", "exercise", "exercise__category") \
            .annotate(best=Max("grade")) \
            .order_by()) # Remove default ordering.
        for submission in submissions:
            student_id = submission["submitters"]
            if student_id in self.results:
                self.results[student_id][submission["exercise"]] = submission["best"]
                self.results_by_category[student_id][submission["exercise__category"]] += submission["best"]


    def results_for_template(self):
        """
        Converts the results data into a form that is convenient for to use in a
        template. The columns of the table ordered according to the order of the
        exercises in self.exercises.
        """
        for_template = []
        for student in self.students:
            grades = [ self.results[student.id][exercise.id] \
                for exercise in self.exercises ]
            total = sum(g for g in grades if g is not None)
            for_template.append((student, grades, total))
        return for_template


    def max_sum(self):
        return sum(e.max_points for e in self.exercises)
