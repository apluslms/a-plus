from datetime import timedelta

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from course.models import Course, CourseInstance, CourseModule
from exercise.models import BaseExercise, CourseChapter, LearningObjectCategory
from exercise.submission_models import Submission

from .submission_sheet import filter_best_submissions
from .views import CourseResultsDataViewSet

class CourseResultsDataViewSetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Make a student
        cls.student = User(username="testUser", first_name="Superb",
                            last_name="Student", email="test@aplus.com")
        cls.student.set_password("testPassword")
        cls.student.save()
        cls.student_profile = cls.student.userprofile
        cls.student_profile.student_id = "12345X"
        cls.student_profile.save()

        cls.student2 = User(username="testUser2", first_name="Superb",
                            last_name="Student", email="test@aplus.com")
        cls.student2.set_password("testPassword")
        cls.student2.save()
        cls.student_profile2 = cls.student2.userprofile
        cls.student_profile2.student_id = "12345Y"
        cls.student_profile2.save()

        # Make a course and course instance
        cls.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        cls.today = timezone.now()
        cls.tomorrow = cls.today + timedelta(days=1)

        cls.course_instance1 = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=cls.today,
            ending_time=cls.tomorrow,
            course=cls.course,
            url="T-00.1000_d1"
        )

        # Add learning object categories to course
        cls.chapter_category = LearningObjectCategory.objects.create(
            name="chapter",
            course_instance=cls.course_instance1
        )
        cls.learning_object_category1 = LearningObjectCategory.objects.create(
            name="test category 1",
            course_instance=cls.course_instance1
        )
        cls.mandatory_category1 = LearningObjectCategory.objects.create(
            name="mandatory category 1",
            confirm_the_level=True,
            course_instance=cls.course_instance1
        )

        cls.module1 = CourseModule.objects.create(
            name="module1",
            url="module1",
            course_instance=cls.course_instance1,
        )

        # Add learning objects to module1
        cls.learning_object1 = BaseExercise.objects.create(
            name="learning object 1",
            url="lo1",
            course_module=cls.module1,
            category=cls.learning_object_category1,
        )
        cls.mandatory_learning_object1 = BaseExercise.objects.create(
            name="mandatory learning object 1",
            url="mlo1",
            course_module=cls.module1,
            category=cls.mandatory_category1,
            points_to_pass=1,
        )

        # Add learning objects to module1
        cls.chapter1 = CourseChapter.objects.create(
            name="chapter 1",
            url="c1",
            course_module=cls.module1,
            category=cls.chapter_category,
        )
        cls.c1_learning_object1 = BaseExercise.objects.create(
            name="c1 learning object 1",
            url="c1lo1",
            course_module=cls.module1,
            parent=cls.chapter1,
            category=cls.learning_object_category1,
        )
        cls.c1_mandatory_learning_object1 = BaseExercise.objects.create(
            name="c1 mandatory learning object 1",
            url="c1mlo1",
            course_module=cls.module1,
            parent=cls.chapter1,
            category=cls.mandatory_category1,
            points_to_pass=1,
        )

        # Add a student to course instance
        cls.course_instance1.enroll_student(cls.student_profile.user)
        cls.course_instance1.enroll_student(cls.student_profile2.user)

    def test_invalidated_submissions_do_not_confirm_sibling_points(self) -> None:
        view = CourseResultsDataViewSet()
        view.instance = self.course_instance1

        def query(show_unconfirmed: bool) -> set[int]:
            rows = view.get_submissions_query(
                [exercise.id],
                self.course_instance1.students,
                [Submission.STATUS.INVALIDATED],
                [exercise.id],
                False,
                show_unconfirmed,
            )
            return {row["exercise_id"] for row in rows}

        for exercise, mandatory_exercise in (
            (self.learning_object1, self.mandatory_learning_object1),
            (self.c1_learning_object1, self.c1_mandatory_learning_object1),
        ):
            with self.subTest(exercise=exercise.id):
                submission = Submission.objects.create(
                    exercise=exercise, grade=1, status=Submission.STATUS.READY,
                )
                submission.submitters.add(self.student_profile)
                confirmation = Submission.objects.create(
                    exercise=mandatory_exercise, grade=2, status=Submission.STATUS.READY,
                )
                confirmation.submitters.add(self.student_profile)
                self.assertEqual(query(False), {exercise.id})

                confirmation.set_invalidated()
                confirmation.save()
                self.assertEqual(query(False), set())
                self.assertEqual(query(True), {exercise.id})

                confirmation.set_revalidated()
                confirmation.save()
                self.assertEqual(query(False), {exercise.id})

    def test_best_submissions_ignore_invalidated_final_submission(self) -> None:
        final_submission = Submission.objects.create(
            exercise=self.learning_object1, grade=2, status=Submission.STATUS.READY, force_exercise_points=True,
        )
        best_submission = Submission.objects.create(
            exercise=self.learning_object1, grade=8, status=Submission.STATUS.READY,
        )
        for submission in (final_submission, best_submission):
            submission.submitters.add(self.student_profile)

        def best_ids(include_all_submissions: bool) -> list[int]:
            submissions = list(
                Submission.objects.filter(exercise=self.learning_object1).order_by('exercise_id', 'id')
            )
            best = filter_best_submissions(submissions, {self.learning_object1.id}, include_all_submissions)
            return [submission.id for submission in best]

        for include_all_submissions in (False, True):
            with self.subTest(include_all_submissions=include_all_submissions):
                self.assertEqual(best_ids(include_all_submissions), [final_submission.id])
                final_submission.set_invalidated()
                final_submission.save()
                self.assertEqual(best_ids(include_all_submissions), [best_submission.id])
                final_submission.set_revalidated()
                final_submission.save()

    def test_best_submissions_exclude_invalidated_high_grade(self) -> None:
        ready_submission = Submission.objects.create(
            exercise=self.learning_object1, grade=8, status=Submission.STATUS.READY,
        )
        invalidated_submission = Submission.objects.create(
            exercise=self.learning_object1, grade=10, status=Submission.STATUS.READY,
        )
        for submission in (ready_submission, invalidated_submission):
            submission.submitters.add(self.student_profile)
        invalidated_submission.set_invalidated()
        invalidated_submission.save()
        revealed_ids = {self.learning_object1.id}

        for grading_mode in (BaseExercise.GRADING_MODE.BEST, BaseExercise.GRADING_MODE.LAST):
            self.learning_object1.grading_mode = grading_mode
            self.learning_object1.save()
            for force_exercise_points in (False, True):
                invalidated_submission.force_exercise_points = force_exercise_points
                invalidated_submission.save(update_fields=['force_exercise_points'])
                for include_all_submissions in (False, True):
                    with self.subTest(
                        grading_mode=grading_mode,
                        force_exercise_points=force_exercise_points,
                        include_all_submissions=include_all_submissions,
                    ):
                        submissions = list(
                            Submission.objects.filter(exercise=self.learning_object1).order_by('exercise_id', 'id')
                        )
                        best = filter_best_submissions(submissions, revealed_ids, include_all_submissions)
                        self.assertEqual([submission.id for submission in best], [ready_submission.id])
                        self.assertEqual(
                            filter_best_submissions([invalidated_submission], revealed_ids, include_all_submissions),
                            [],
                        )

    def test_get_submissions_query_unconfirmed_points(self):
        def query(unconfirmed: bool):
            qset = view.get_submissions_query(
                ids,
                self.course_instance1.students,
                [],
                ids,
                True,
                unconfirmed,
            )
            return {(row["submitters__user_id"], row["exercise_id"], row["count"]) for row in qset}

        def create_submission(user_profile, exercise, **kwargs):
            nonlocal submissions
            sub = Submission.objects.create(exercise=exercise, **kwargs)
            sub.submitters.add(user_profile)

            submissions.setdefault((user_profile.user_id, exercise.id), [0, False])
            submissions[(user_profile.user_id, exercise.id)][0] += 1

            if exercise.category.confirm_the_level and sub.grade >= exercise.points_to_pass:
                if exercise.parent is not None:
                    children = exercise.parent.children.all()
                else:
                    children = [lo for lo in exercise.course_module.learning_objects.all() if lo.parent is None]

                for c in children:
                    if (user_profile.user_id, c.id) in submissions:
                        submissions[(user_profile.user_id, c.id)][1] = True

            return (user_profile.user_id, exercise.id, 1)

        def all_submissions():
            nonlocal submissions
            return {
                (user_id, ex_id, count)
                for (user_id, ex_id), (count, confirmed) in submissions.items()
            }

        def confirmed_submissions():
            nonlocal submissions
            return {
                (user_id, ex_id, count)
                for (user_id, ex_id), (count, confirmed) in submissions.items()
                if confirmed
            }

        view = CourseResultsDataViewSet()
        view.instance = self.course_instance1

        submissions = {}

        ids = [
            self.learning_object1.id,
            self.mandatory_learning_object1.id,
            self.c1_learning_object1.id,
            self.c1_mandatory_learning_object1.id,
        ]

        create_submission(self.student_profile, exercise=self.learning_object1)
        create_submission(self.student_profile, exercise=self.c1_learning_object1)
        create_submission(self.student_profile2, exercise=self.learning_object1)
        create_submission(self.student_profile2, exercise=self.c1_learning_object1)

        self.assertEqual(query(True), all_submissions())
        self.assertEqual(query(False), confirmed_submissions())


        create_submission(self.student_profile, exercise=self.mandatory_learning_object1, grade=2)

        self.assertEqual(query(True), all_submissions())
        self.assertEqual(query(False), confirmed_submissions())


        create_submission(self.student_profile, exercise=self.c1_mandatory_learning_object1, grade=2)

        self.assertEqual(query(True), all_submissions())
        self.assertEqual(query(False), confirmed_submissions())


        create_submission(self.student_profile2, exercise=self.c1_mandatory_learning_object1, grade=0)

        self.assertEqual(query(True), all_submissions())
        self.assertEqual(query(False), confirmed_submissions())

        create_submission(self.student_profile2, exercise=self.c1_mandatory_learning_object1, grade=2)

        self.assertEqual(query(True), all_submissions())
        self.assertEqual(query(False), confirmed_submissions())
