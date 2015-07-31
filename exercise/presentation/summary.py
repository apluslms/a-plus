from exercise.models import BaseExercise


class UserExerciseSummary(object):
    """
    UserExerciseSummary summarises the submissions of a certain user and
    exercise. It calculates some characterizing figures such as the number of
    submissions and reference to the best submission. See the public methods
    for more.
    """
    def __init__(self, exercise, user=None, **kwargs):
        self.exercise = exercise
        self.user = user
        self.submission_count = kwargs.get("submission_count", 0)
        self.best_submission = kwargs.get("best_submission", None)

        # The caller of the __init__ may give kwargs submission_count and
        # best_submission in advance together with generate=False in which case
        # the __init__ will not query the Submission model at all. This is used
        # by the UserCourseSummary which has to generate a UserExerciseSummary
        # for every exercise.
        if kwargs.get("generate", True):
            self._generate_summary()

    def _generate_summary(self):
        if self.user and self.user.is_authenticated():
            submissions = self.exercise \
                .get_submissions_for_student(self.user.userprofile) \
                .order_by('-grade', 'id')
            self.submission_count = submissions.count()
            self.best_submission = submissions.first()

    def get_submission_count(self):
        return self.submission_count

    def get_best_submission(self):
        return self.best_submission

    def get_max_points(self):
        return self.exercise.max_points

    def get_points(self):
        return self.best_submission.grade if self.best_submission else 0

    def get_total_points(self):
        return self.get_points()

    def get_required_points(self):
        return self.exercise.points_to_pass

    def is_full_points(self):
        return self.get_points() >= self.exercise.max_points

    def is_passed(self):
        return self.get_points() >= self.exercise.points_to_pass

    def is_submitted(self):
        return self.submission_count > 0


class UserModuleSummary(object):
    """
    Summarises the submissions of a certain user in a course module.

    """
    def __init__(self, module, user=None, **kwargs):
        self.module = module
        self.user = user
        self.exercise_summaries = kwargs.get("exercise_summaries", [])

        if kwargs.get("generate", True):
            self._generate_summary()

        self.exercise_count = len(self.exercise_summaries)
        self.max_points = sum(summary.get_max_points() \
            for summary in self.exercise_summaries)
        self.total_points = sum(summary.get_points() \
            for summary in self.exercise_summaries)

    def _generate_summary(self):
        for ex in BaseExercise.objects.filter(course_module=self.module):
            self.exercise_summaries.append(UserExerciseSummary(ex, self.user))

    def get_exercise_count(self):
        return self.exercise_count

    def get_max_points(self):
        return self.max_points

    def get_total_points(self):
        return self.total_points

    def get_required_points(self):
        return self.module.points_to_pass

    def is_passed(self):
        if self.total_points < self.module.points_to_pass:
            return False
        for es in self.exercise_summaries:
            if not es.is_passed():
                return False
        return True


class UserCategorySummary(object):
    """
    Summarises the submissions of a certain user in an exercise category.

    """
    def __init__(self, category, user=None, **kwargs):
        self.category = category
        self.user = user
        self.exercise_summaries = kwargs.get("exercise_summaries", [])

        if kwargs.get("generate", True):
            self._generate_summary()

        self.exercise_count = len(self.exercise_summaries)
        self.max_points = sum(summary.get_max_points() \
            for summary in self.exercise_summaries)
        self.total_points = sum(summary.get_points() \
            for summary in self.exercise_summaries)

    def _generate_summary(self):
        for ex in BaseExercise.objects.filter(category=self.category):
            self.exercise_summaries.append(UserExerciseSummary(ex, self.user))

    def get_exercise_count(self):
        return self.exercise_count

    def get_max_points(self):
        return self.max_points

    def get_total_points(self):
        return self.total_points

    def get_required_points(self):
        return self.category.points_to_pass

    def is_passed(self):
        if self.total_points < self.category.points_to_pass:
            return False
        for es in self.exercise_summaries:
            if not es.is_passed():
                return False
        return True


class UserCourseSummary(object):
    """
    UserCourseSummary generates a personal summary for a user of the exercises
    existing and completed on a given course.

    UserCourseSummary is designed so that it queries the Submission model only
    once and builds the related UserModuleSummary objects,
    UserCategorySummary objects and UserExerciseSummary objects so that the
    generation of those related objects will not cause additional model
    queries. This is crucial for performance as the UserCourseSummary is
    generated for the most loaded pages of A+ and thus needs to be as fast as
    possible.
    """
    def __init__(self, course_instance, user=None):
        self.course_instance = course_instance
        self.user = user

        # QuerySets.
        self.modules = course_instance.course_modules.all()
        self.categories = course_instance.categories.all()
        self.exercises = list(BaseExercise.objects \
            .filter(course_module__course_instance=self.course_instance) \
            .select_related("course_module", "category"))
        self.submissions = list(user.userprofile.submissions \
            .filter(exercise__course_module__course_instance=self.course_instance) \
            .defer("feedback", "assistant_feedback", "submission_data", "grading_data")) \
            if user and user.is_authenticated() else []

        self.exercise_count = len(self.exercises)
        self.max_points = sum(exercise.max_points for exercise in self.exercises)

        # Summaries to be generated.
        self.exercise_summaries = {}
        self.module_summaries = {}
        self.category_summaries = {}
        self.visible_category_summaries = {}
        self.total_points = 0

        self._generate_summary()

    def _generate_summary(self):
        """
        Generates the different user summaries.
        """
        submissions_by_exercise_id = {
            exercise.id: {
                "obj": exercise,
                "count": 0,
                "best": None
            } for exercise in self.exercises
        }

        # Count submissions and find the best.
        for submission in self.submissions:
            d = submissions_by_exercise_id[submission.exercise_id]
            d["count"] += 1
            if not d["best"] or submission.grade >= d["best"].grade:
                d["best"] = submission

        exercise_summaries_by_course_modules = {
            course_module: [] for course_module in self.modules
        }
        exercise_summaries_by_categories = {
            category: [] for category in self.categories
        }

        # Generate summary for each exercise. We have already found out the
        # best submission and submission count for each UserExerciseSummary so
        # we just pass those to the __init__ of each UserExerciseSummary and
        # use the generate=False to tell the __init__ that it doesn't need to
        # make any additional model queries.
        for eid, d in list(submissions_by_exercise_id.items()):
            best = d["best"]
            if best:
                self.total_points += best.grade
            exercise_summary = UserExerciseSummary(
                d["obj"],
                self.user,
                submission_count=d["count"],
                best_submission=best,
                generate=False
            )
            exercise_summaries_by_course_modules[d["obj"].course_module] \
                .append(exercise_summary)
            exercise_summaries_by_categories[d["obj"].category] \
                .append(exercise_summary)
            self.exercise_summaries[eid] = exercise_summary

        # Generate a summary for each course module.
        for module, exercise_summaries \
                in list(exercise_summaries_by_course_modules.items()):
            self.module_summaries[module.id] = UserModuleSummary(
                module,
                self.user,
                exercise_summaries=exercise_summaries,
                generate=False)

        # Generate a summary for each category.
        user_hidden_categories = \
            list(self.user.userprofile.hidden_categories.all())
        for category, exercise_summaries \
                in list(exercise_summaries_by_categories.items()):
            summary = UserCategorySummary(
                category,
                self.user,
                exercise_summaries=exercise_summaries,
                generate=False)
            self.category_summaries[category.id] = summary
            if not category in user_hidden_categories:
                self.visible_category_summaries[category.id] = summary

    def get_category_summary(self, category):
        return self.category_summaries[category.id]

    def get_module_summary(self, course_module):
        return self.module_summaries[course_module.id]

    def get_exercise_summary(self, exercise):
        return self.exercise_summaries[exercise.id]

    def get_exercise_count(self):
        return self.exercise_count

    def get_max_points(self):
        return self.max_points

    def get_total_points(self):
        return self.total_points

    def get_required_points(self):
        return None

    def is_passed(self):
        for summary in self.module_summaries.values():
            if summary.is_passed() == False:
                return False
        return True
