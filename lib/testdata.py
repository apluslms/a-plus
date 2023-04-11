from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.test import TestCase
from django.utils import timezone

from course.models import (
    Course,
    CourseInstance,
    CourseModule,
    LearningObjectCategory,
)
from exercise.models import (
    BaseExercise,
    StaticExercise,
    Submission,
)


class CourseTestCase(TestCase):

    def setUp(self):
        self.setUpCourse()
        self.setUpSubmissions()

    def setUpCourse(self):

        self.now = timezone.now()
        self.tomorrow = self.now + timedelta(days=1)
        self.two_days_after = self.now + timedelta(days=2)
        self.three_days_after = self.now + timedelta(days=3)
        self.yesterday = self.now - timedelta(days=1)
        self.two_days_before = self.now - timedelta(days=2)

        self.user = User(username='testUser')
        self.user.set_password('testPassword')
        self.user.save()

        self.teacher = User(username='testTeacher')
        self.teacher.set_password('testPassword')
        self.teacher.save()

        self.student = User(username='testStudent')
        self.student.set_password('testPassword')
        self.student.save()
        self.student.userprofile.student_id = "123TEST"
        self.student.userprofile.organization = settings.LOCAL_ORGANIZATION
        self.student.userprofile.save()

        self.course = Course.objects.create(
            url="course",
            name="Test Course",
            code="123456",
        )

        self.instance = CourseInstance.objects.create(
            course=self.course,
            url="instance",
            instance_name="2016",
            starting_time=self.now,
            ending_time=self.tomorrow,
        )
        self.instance.add_teacher(self.teacher.userprofile)
        self.instance.enroll_student(self.student)

        self.module = CourseModule.objects.create(
            course_instance=self.instance,
            url="module",
            name="Test Module",
            points_to_pass=10,
            opening_time=self.now,
            closing_time=self.tomorrow,
            late_submissions_allowed=True,
            late_submission_deadline=self.two_days_after,
            late_submission_penalty=0.2
        )
        self.module2 = CourseModule.objects.create(
            course_instance=self.instance,
            url="module2",
            name="Test Module 2",
            points_to_pass=0,
            opening_time=self.tomorrow,
            closing_time=self.two_days_after,
        )
        self.module0 = CourseModule.objects.create(
            course_instance=self.instance,
            url="module0",
            name="Past Module",
            points_to_pass=10,
            opening_time=self.two_days_before,
            closing_time=self.yesterday,
        )
        self.category = LearningObjectCategory.objects.create(
            course_instance=self.instance,
            name="Test Category",
            points_to_pass=5,
        )

        self.exercise = StaticExercise.objects.create(
            course_module=self.module,
            category=self.category,
            url='e1',
            name="Test Exercise",
            exercise_page_content='$$exercise$$content',
            submission_page_content='$$exercise$$received',
            points_to_pass=0,
            max_points=100,
            order=1,
        )
        self.exercise2 = StaticExercise.objects.create(
            course_module=self.module,
            category=self.category,
            url='e2',
            name="Test Exercise 2",
            exercise_page_content='$$exercise2$$content',
            submission_page_content='$$exercise2$$received',
            points_to_pass=10,
            max_points=100,
            order=2,
        )
        self.exercise3 = StaticExercise.objects.create(
            course_module=self.module2,
            category=self.category,
            url='e3',
            name="Test Exercise 3",
            exercise_page_content='$$exercise3$$content',
            submission_page_content='$$exercise3$$received',
            points_to_pass=0,
            max_points=100,
        )
        self.exercise0 = BaseExercise.objects.create(
            course_module=self.module0,
            category=self.category,
            url='b0',
            name="Base Exercise 0",
            service_url="http://localhost/",
            points_to_pass=0,
            max_points=100,
            min_group_size=1,
            max_group_size=2,
        )

    def setUpSubmissions(self):

        self.submission = Submission.objects.create(
            exercise=self.exercise,
            submission_data={'submission':1},
            feedback='$$submission$$feedback',
        )
        self.submission.submitters.add(self.student.userprofile)
        self.submission.set_points(1,2)
        self.submission.set_ready()
        self.submission.save()

        self.submission2 = Submission.objects.create(
            exercise=self.exercise,
            submission_data={'submission':2},
        )
        self.submission2.submitters.add(self.student.userprofile)

        self.submission3 = Submission.objects.create(
            exercise=self.exercise2,
            submission_data={'submission':3},
        )
        self.submission3.submitters.add(self.student.userprofile)
        self.submission3.submitters.add(self.user.userprofile)
