# Python
from datetime import datetime
from operator import attrgetter

# Django
from django.utils import simplejson
from django.db.models.aggregates import Avg, Max, Sum

# A+
from exercise.exercise_models import *
from exercise.submission_models import Submission


class ExerciseSummary:
    def __init__(self, exercise, user, submission_count=0,
                 best_submission=None, generate=True):
        self.exercise = exercise
        self.user = user
        self.submission_count = submission_count
        self.best_submission = best_submission

        if generate:
            self._generate_summary()

    def _generate_summary(self):
        """
        Initializes the instance variables submission_count and
        best_submission. The best submission is the submission with the highest
        grade and latest id.

        If submissions is given as an argument, the method is optimized so that
        no database queries are used.
        """
        submissions = self.exercise.get_submissions_for_student(
            self.user.get_profile()).order_by('-grade', 'id')

        self.submission_count = submissions.count()

        if self.submission_count != 0:
            self.best_submission = submissions[0]

    def get_max_points(self):
        return self.exercise.max_points

    def get_points(self):
        if self.best_submission == None:
            return 0
        return self.best_submission.grade

    def get_completed_percentage(self):
        if self.get_max_points() == 0:
            return 0
        else:
            return int(round(100.0
                             * self.get_points()
                             / self.get_max_points()))

    def get_required_percentage(self):
        if self.get_max_points() == 0:
            return 0
        else:
            return int(round(100.0
                             * self.exercise.points_to_pass
                             / self.get_max_points()))

    def get_average_percentage(self):
        if self.get_max_points() == 0:
            return 0
        else:
            return int(round(100.0
                             # TODO: Slow?
                             * self.exercise.summary["average_grade"]
                             / self.get_max_points()))

    def is_full_points(self):
        return self.get_points() == self.exercise.max_points

    def is_passed(self):
        return self.get_points() >= self.exercise.points_to_pass

    def is_submitted(self):
        return self.submission_count > 0


class ExerciseRoundSummary:
    def __init__(self, exercise_round, user, exercise_summaries=[],
                 generate=True):
        self.exercise_round = exercise_round
        self.user = user
        self.exercises = BaseExercise.objects.filter(
            course_module=self.exercise_round)
        self.exercise_summaries = exercise_summaries

        self.points_available = 0
        self.exercises_passed = 0
        self.categories = []
        self.visible_categories = []

        # This is a list of tuples where the first item is a
        # LearningObjectCategory object and the second item is a list of
        # exercises.
        self.categorized_exercise_summaries = []

        if generate:
            self._generate_summary()

    def _generate_summary(self):
        submissions = Submission.objects.filter(
            exercise__course_module=self.exercise_round,
            submitters=self.user).select_related("exercise")

        submissions_by_exercises = {exercise: []
                                    for exercise in self.exercises}

        for submission in submissions:
            submissions_by_exercises[submission.exercise].append(submission)

        for exercise, submissions in submissions_by_exercises.items():
            ex_summary = ExerciseSummary(exercise,
                                         self.user)
            self.exercise_summaries.append(ex_summary)

            if (len(self.categorized_exercise_summaries) == 0
                or exercise.category
                    != self.categorized_exercise_summaries[-1][0]):
                self.categorized_exercise_summaries.append(
                    (exercise.category, []))
            self.categorized_exercise_summaries[-1][1].append(ex_summary)

            if not exercise.category in self.categories:
                self.categories.append(exercise.category)

        for category in self.categories:
            if (not category.is_hidden_to(self.user.get_profile())
                and not category in self.visible_categories):
                self.visible_categories.append(category)

    def get_total_points(self):
        total                   = 0
        for ex_summary in self.exercise_summaries:
            total += ex_summary.get_points()
        return total

    def get_maximum_points(self):
        total                   = 0
        for ex_summary in self.exercise_summaries:
            total += ex_summary.get_max_points()
        return total

    def get_average_total_grade(self):
        return sum([exercise.summary["average_grade"] for exercise in self.exercises])

    def has_visible_categories(self):
        return len(self.visible_categories) > 0

    def is_passed(self):
        """
        Returns True or False based on if the student has passed the exercise round
        or not. The round is passed if the total points are equal to or higher than
        minimum for the round and if each individual exercise in the round is passed.
        """
        if self.get_total_points() < self.exercise_round.points_to_pass:
            return False

        for es in self.exercise_summaries:
            if not es.is_passed():
                return False

        return True

    def get_exercise_count(self):
        return self.exercises.count()

    def get_classes(self):
        """
        Returns the CSS classes that should be used for 
        this exercise round in the exercise view.
        """
        classes = []
        if self.exercise_round.opening_time > datetime.now():
            classes.append("upcoming")
            classes.append("collapsed")

        elif self.exercise_round.closing_time < datetime.now():
            classes.append("closed")
            classes.append("collapsed")

        else:
            classes.append("open")

        return " ".join(classes)

    def get_completed_percentage(self):
        max_points = self.get_maximum_points()
        if max_points == 0:
            return 0
        else:
            return int(round(100.0 * self.get_total_points() / max_points))

    def get_required_percentage(self):
        if self.get_maximum_points() == 0:
            return 0
        else:
            return int(round(100.0 * self.exercise_round.points_to_pass / self.get_maximum_points()))


class CategorySummary:
    def __init__(self, category, user, exercise_summaries=[], generate=True):
        self.category = category
        self.user = user
        self.exercises = BaseExercise.objects.filter(category=category)

        self.exercise_summaries = exercise_summaries

        if generate:
            self._generate_summary()

    def _generate_summary(self):
        for ex in self.exercises:
            self.exercise_summaries.append(ExerciseSummary(ex, self.user))

    def get_average_total_grade(self):
        return sum([exercise.summary["average_grade"]
                    for exercise in self.exercises])

    def get_completed_percentage(self):
        max_points = self.get_maximum_points()
        if max_points == 0:
            return 0
        else:
            return int(round(100.0 * self.get_total_points() / max_points))

    def get_maximum_points(self):
        total = 0
        for ex_summary in self.exercise_summaries:
            total += ex_summary.get_max_points()
        return total

    def get_required_percentage(self):
        if self.get_maximum_points() == 0:
            return 0
        else:
            return int(round(
                100.0 * self.category.points_to_pass
                / self.get_maximum_points()))

    def get_total_points(self):
        total = 0
        for ex_summary in self.exercise_summaries:
            total += ex_summary.get_points()
        return total

    def is_hidden(self):
        return self.category.is_hidden_to(self.user.get_profile())

    def is_passed(self):
        # TODO: Implement
        return False


class CourseSummary:
    """ 
    Course summary generates a personal summary for a user of the exercises
    existing and completed on a given course. 
    """
    def __init__(self, course_instance, user):
        self.course_instance = course_instance
        self.user = user
        self.exercise_rounds = course_instance.course_modules.all()
        self.categories = course_instance.categories.all()
        self.exercises = BaseExercise.objects.filter(
            course_module__course_instance=self.course_instance).select_related("course_module", "category")
        self.submissions = user.get_profile().submissions.filter(
            exercise__course_module__course_instance=self.course_instance).defer("feedback")

        self.round_summaries = []
        self.visible_round_summaries = []
        self.category_summaries = []
        self.visible_category_summaries = []

        self._generate_summary()

    def is_passed(self):
        for round_summary in self.round_summaries:
            if round_summary.is_passed() == False:
                return False
        return True

    def get_exercise_count(self):
        exercise_count = 0
        for round_summary in self.round_summaries:
            exercise_count += round_summary.get_exercise_count()
        return exercise_count

    def get_maximum_points(self):
        """
        Returns the maximum points for the whole course instance, ie. the sum of 
        maximum points for all exercises.
        """
        all_exercises   = BaseExercise.objects.filter(course_module__course_instance=self.course_instance)
        max_points      = all_exercises.aggregate(max_points=Sum('max_points'))['max_points']
        return max_points or 0

    def get_total_points(self):
        point_sum = 0
        for ex_round in self.round_summaries:
            point_sum += ex_round.get_total_points()
        return point_sum

    def get_json_by_rounds(self):
        round_list = []
        for round_summary in self.round_summaries:
            round_list.append( [round_summary.exercise_round.name,
                                round_summary.get_total_points(),
                                round_summary.get_average_total_grade(),
                                round_summary.get_maximum_points(),
                                ])
        return simplejson.dumps(round_list)

    def get_completed_percentage(self):
        max_points = self.get_maximum_points()
        if max_points == 0:
            return 0
        else:
            return int(round(100.0 * self.get_total_points() / max_points))

    def _generate_summary(self):
        # Generate a summary of each exercise round
        submissions_by_exercise_id = {exercise.id: {"obj": exercise,
                                                    "count": 0,
                                                    "best": None}
                                      for exercise in self.exercises}

        for submission in self.submissions:
            d = submissions_by_exercise_id[submission.exercise_id]
            d["count"] += 1
            if not d["best"] or submission.grade > d["best"].grade:
                d["best"] = submission

        exercise_summaries_by_course_modules = {course_module: []
                                                for course_module
                                                in self.exercise_rounds}
        exercise_summaries_by_categories = {category: []
                                            for category in self.categories}

        # Generate summary for each exercise
        for exercise_id, d in submissions_by_exercise_id.items():
            best_submission = d["best"]
            submission_count = d["count"]
            exercise_summary = ExerciseSummary(
                d["obj"], self.user, submission_count=submission_count,
                best_submission=best_submission, generate=False)

            (exercise_summaries_by_course_modules[d["obj"].course_module]
             .append(exercise_summary))

            (exercise_summaries_by_categories[d["obj"].category]
             .append(exercise_summary))

        # Generate a summary for each round
        for rnd, exercise_summaries in (exercise_summaries_by_course_modules
                                        .items()):
            self.round_summaries.append(ExerciseRoundSummary(
                rnd, self.user, exercise_summaries, generate=False))

        # Generate a summary for each category
        for cat, exercise_summaries in (exercise_summaries_by_categories
                                        .items()):
            self.category_summaries.append(CategorySummary(
                cat, self.user, exercise_summaries, generate=False))

        # Separate list for visible category summaries only
        user_hidden_categories = (self.user.get_profile()
                                  .hidden_categories.all())
        for cat_sum in self.category_summaries:
            if not cat_sum.category in user_hidden_categories:
                self.visible_category_summaries.append(cat_sum)

        # Separate list for round summaries that have visible categories
        for rnd_sum in self.round_summaries:
            if rnd_sum.has_visible_categories():
                self.visible_round_summaries.append(rnd_sum)