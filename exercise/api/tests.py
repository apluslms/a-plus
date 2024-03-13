from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from course.models import Course, CourseInstance
from exercise.models import LearningObjectCategory
from django.utils import timezone
from datetime import timedelta

class ExerciceSubmissionAPITest(TestCase):
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

        # Make a course and course instance
        cls.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        cls.today = timezone.now()
        cls.tomorrow = cls.today + timedelta(days=1)
        cls.two_days_from_now = cls.tomorrow + timedelta(days=1)

        cls.course_instance1 = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=cls.today,
            ending_time=cls.tomorrow,
            course=cls.course,
            url="T-00.1000_d1"
        )

        # Add learning object category to course
        cls.learning_object_category1 = LearningObjectCategory.objects.create(
            name="test category 1",
            course_instance=cls.course_instance1
        )

        # Add learning object to that category
        #cls.learning_object_category1.

        # Add a student to course instance
        cls.course_instance1.enroll_student(cls.student_profile.user)

    # Not finished
    def test_post_submission(self):
        """
        Test that making a submission to exercise with id 1 works
        """
        client = APIClient()
        client.force_authenticate(user=self.student)
        # pylint: disable-next=unused-variable
        response = client.post('/api/v2/exercises/1/submissions/', {'code':'12esf43tdfaE3rS'})
        # FIXME: test doesn't create submission, thus this resource is 404
        #self.assertEqual(response.data, None)

    def test_get_submissions(self):
        """
        Test that getting user's submissions to exercise with id 1 works
        """
        client = APIClient()
        client.force_authenticate(user=self.student)
        response = client.get('/api/v2/exercises/1/submissions/') # pylint: disable=unused-variable
        # FIXME: test doesn't create submission, thus this resource is 404
        #self.assertEqual(response.data, {
        #    'count': 0,
        #    'next': None,
        #    'previous': None,
        #    'results': []
        #})

    def test_get_submissiondetail(self):
        """
        Test that getting a submission with id 1 to exercise with
        id 1 works
        """
        client = APIClient()
        client.force_authenticate(user=self.student)
        response = client.get('/api/v2/submissions/1/')
        self.assertEqual(response.data, {'detail': 'Not found.'})
