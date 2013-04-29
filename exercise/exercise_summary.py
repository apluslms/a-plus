# Python
from datetime import datetime
from operator import attrgetter

# Django
from django.utils import simplejson
from django.db.models.aggregates import Sum

# A+
from exercise.exercise_models import BaseExercise
from exercise.submission_models import Submission


class UserExerciseSummary(object):
    """
    UserExerciseSummary summarises the submissions of a certain user and
    exercise. It calculates some characterizing figures such as the number of
    submissions and reference to the best submission. See the public methods
    for more.
    """
    def __init__(self, exercise, user, **kwargs):
        """
        @param exercise: instance of BaseExercise
        @param user: instance of Django User
        """
        self.exercise = exercise
        self.user = user
        self.submission_count = getattr(kwargs, "submission_count", 0)
        self.best_submission = getattr(kwargs, "best_submission", None)

        # The caller of the __init__ may give kwargs submission_count and
        # best_submission in advance together with generate=False in which case
        # the __init__ will not query the Submission model at all. This is used
        # by the UserCourseSummary which has to generate a UserExerciseSummary
        # for every exercise.
        if getattr(kwargs, "generate", True):
            self._generate_summary()

    def _generate_summary(self):
        """
        Initializes the instance variables submission_count and
        best_submission.
        """
        submissions = self.exercise.get_submissions_for_student(
            self.user.get_profile()).order_by('-grade', 'id')

        self.submission_count = submissions.count()

        if self.submission_count != 0:
            self.best_submission = submissions[0]

    def get_best_submission(self):
        """
        The best_submission is the submission with the highest
        grade and latest id.

        @return: Submission instance
        """
        return self.best_submission

    def get_completed_percentage(self):
        """
        Rounds to closest int.

        @return: 0..100 as int
        """
        if self.exercise.max_points == 0:
            return 0
        else:
            return int(round(100.0
                             * self.get_points()
                             / self.exercise.max_points))

    def get_points(self):
        """
        Gives the points of the best submission of the user or 0 if there are
        no submissions for the user.

        @return: best points as an int
        """
        if not self.best_submission:
            return 0
        return self.best_submission.grade

    def get_submission_count(self):
        """
        Number of submissions to this exercise made by this user.

        @return: int
        """
        return self.submission_count

    def is_full_points(self):
        return self.get_points() == self.exercise.max_points

    def is_passed(self):
        return self.get_points() >= self.exercise.points_to_pass

    def is_submitted(self):
        return self.submission_count > 0


class UserExerciseRoundSummary(object):
    """
    Summarises the submissions of a certain user and exercise round.
    """
    def __init__(self, exercise_round, user, **kwargs):
        """
        @param exercise_round: instance of CourseModule
        @param user: instance of Django User
        """
        self.exercise_round = exercise_round
        self.user = user
        self.exercises = BaseExercise.objects.filter(
            course_module=self.exercise_round)
        self.exercise_summaries = getattr(kwargs, "exercise_summaries", [])

        if getattr(kwargs, "generate", True):
            self._generate_summary()

        self.categories = []
        self.visible_categories = []

        # This is a list of tuples where the first item is a
        # LearningObjectCategory object and the second item is a list of
        # exercise summaries.
        self.categorized_exercise_summaries = []

        for ex_summary in sorted(self.exercise_summaries,
                                 key=lambda summ: summ.exercise.order):
            if (len(self.categorized_exercise_summaries) == 0
                or ex_summary.exercise.category
                    != self.categorized_exercise_summaries[-1][0]):
                self.categorized_exercise_summaries.append(
                    (ex_summary.exercise.category, []))
            self.categorized_exercise_summaries[-1][1].append(ex_summary)

            if not ex_summary.exercise.category in self.categories:
                self.categories.append(ex_summary.exercise.category)

        for category in self.categories:
            if (not category.is_hidden_to(self.user.get_profile())
                    and not category in self.visible_categories):
                self.visible_categories.append(category)

    def _generate_summary(self):
        # TODO: This could also use the optimisation technique for generating
        # the ExerciseSummary objects.
        for exercise in self.exercises:
            ex_summary = UserExerciseSummary(exercise, self.user)
            self.exercise_summaries.append(ex_summary)

    def get_total_points(self):
        total = 0
        for ex_summary in self.exercise_summaries:
            total += ex_summary.get_points()
        return total

    def get_average_total_grade(self):
        return sum([exercise.summary["average_grade"] for exercise
                    in self.exercises])

    def has_visible_categories(self):
        return len(self.visible_categories) > 0

    def is_passed(self):
        """
        Returns True or False based on if the student has passed the exercise
        round or not. The round is passed if the total points are equal to or
        higher than minimum for the round and if each individual exercise in
        the round is passed.
        """
        if self.get_total_points() < self.exercise_round.points_to_pass:
            return False

        for es in self.exercise_summaries:
            if not es.is_passed():
                return False

        return True

    def get_exercise_count(self):
        return self.exercises.count()

    def get_completed_percentage(self):
        max_points = self.exercise_round.get_maximum_points()
        if max_points == 0:
            return 0
        else:
            return int(round(100.0 * self.get_total_points() / max_points))


class UserCategorySummary(object):
    def __init__(self, category, user, exercise_summaries=[], generate=True):
        self.category = category
        self.user = user
        self.exercises = BaseExercise.objects.filter(category=category)

        self.exercise_summaries = exercise_summaries

        if generate:
            self._generate_summary()

    def _generate_summary(self):
        for ex in self.exercises:
            self.exercise_summaries.append(UserExerciseSummary(ex, self.user))

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
            total += ex_summary.exercise.max_points
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


class UserCourseSummary(object):
    """ 
    UserCourseSummary generates a personal summary for a user of the exercises
    existing and completed on a given course.

    UserCourseSummary is designed so that it queries the Submission model only
    once and builds the related UserExerciseRoundSummary objects,
    UserCategorySummary objects and UserExerciseSummary objects so that the
    generation of those related objects will not cause additional model
    queries. This is crucial for performance as the UserCourseSummary is
    generated for the most loaded pages of A+ and thus needs to be as fast as
    possible.
    """
    def __init__(self, course_instance, user):
        self.course_instance = course_instance
        self.user = user

        # QuerySets
        self.exercise_rounds = course_instance.course_modules.all()
        self.categories = course_instance.categories.all()
        self.exercises = (BaseExercise.objects.filter(
            course_module__course_instance=self.course_instance)
            .select_related("course_module", "category"))
        self.submissions = (user.get_profile().submissions.filter(
            exercise__course_module__course_instance=self
            .course_instance).defer("feedback"))

        # Summaries to be generated.
        self.exercise_summaries = {}
        self.round_summaries = []
        self.category_summaries = []
        self.visible_category_summaries = []

        # Generate all the summaries!
        self._generate_summary()

    def _generate_summary(self):
        # This method is only called from __init__ and the purpose this code is
        # separated to its own method is readability.

        submissions_by_exercise_id = {exercise.id: {"obj": exercise,
                                                    "count": 0,
                                                    "best": None}
                                      for exercise in self.exercises}

        # Lets go through all the submissions and keep track of the best
        # submission and the count of the submissions for each exercise.
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

        # Generate summary for each exercise. We have already found out the
        # best submission and submission count for each UserExerciseSummary so
        # we just pass those to the __init__ of each UserExerciseSummary and
        # use the generate=False to tell the __init__ that it doesn't need to
        # make any additional model queries.
        for exercise_id, d in submissions_by_exercise_id.items():
            best_submission = d["best"]
            submission_count = d["count"]
            exercise_summary = UserExerciseSummary(
                d["obj"], self.user, submission_count=submission_count,
                best_submission=best_submission, generate=False)

            (exercise_summaries_by_course_modules[d["obj"].course_module]
             .append(exercise_summary))

            (exercise_summaries_by_categories[d["obj"].category]
             .append(exercise_summary))

            self.exercise_summaries[d["obj"]] = exercise_summary

        # Generate a summary for each round
        for rnd, exercise_summaries in (exercise_summaries_by_course_modules
                                        .items()):
            self.round_summaries.append(UserExerciseRoundSummary(
                rnd, self.user, exercise_summaries=exercise_summaries,
                generate=False))

        # Generate a summary for each category
        for cat, exercise_summaries in (exercise_summaries_by_categories
                                        .items()):
            self.category_summaries.append(UserCategorySummary(
                cat, self.user, exercise_summaries, generate=False))

        # Separate list for visible category summaries only
        user_hidden_categories = (self.user.get_profile()
                                  .hidden_categories.all())
        for cat_sum in self.category_summaries:
            if not cat_sum.category in user_hidden_categories:
                self.visible_category_summaries.append(cat_sum)

    def get_category_summary(self, category):
        # TODO: Could self.category_summaries be a dict?
        for category_summary in self.category_summaries:
            if category_summary.category == category:
                return category_summary

    def get_completed_percentage(self):
        max_points = self.get_maximum_points()
        if max_points == 0:
            return 0
        else:
            return int(round(100.0 * self.get_total_points() / max_points))

    def get_exercise_count(self):
        exercise_count = 0
        for round_summary in self.round_summaries:
            exercise_count += round_summary.get_exercise_count()
        return exercise_count

    def get_exercise_round_summary(self, course_module):
        # TODO: Could self.round_summaries be a dict?
        for round_summary in self.round_summaries:
            if round_summary.exercise_round == course_module:
                return round_summary

    def get_exercise_summary(self, exercise):
        return self.exercise_summaries[exercise]

    def get_json_by_rounds(self):
        round_list = []
        for round_summary in self.round_summaries:
            round_list.append([round_summary.exercise_round.name,
                               round_summary.get_total_points(),
                               round_summary.get_average_total_grade(),
                               round_summary.exercise_round
                               .get_maximum_points()])
        return simplejson.dumps(round_list)

    def get_maximum_points(self):
        """
        Returns the maximum points for the whole course instance, ie. the sum
        of maximum points for all exercises.
        """
        all_exercises = BaseExercise.objects.filter(
            course_module__course_instance=self.course_instance)
        max_points = all_exercises.aggregate(
            max_points=Sum('max_points'))['max_points']
        return max_points or 0

    def get_total_points(self):
        point_sum = 0
        for ex_round in self.round_summaries:
            point_sum += ex_round.get_total_points()
        return point_sum

    def is_passed(self):
        for round_summary in self.round_summaries:
            if round_summary.is_passed() == False:
                return False
        return True