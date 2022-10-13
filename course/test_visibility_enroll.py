from datetime import timedelta
import logging

from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from django.conf import settings

from course.models import Course, CourseInstance, CourseModule, \
    LearningObjectCategory
from exercise.exercise_models import BaseExercise, CourseChapter, LearningObject
from exercise.submission_models import Submission

class CourseVisibilityTest(TestCase):
    """Tests for course visibility and access control.
    There are also some tests about enrollment.
    """

    def setUp(self):
        self.user = User(username="testUser") # not enrolled in the course
        self.user.set_password("testUser")
        self.user.save()
        self.user.userprofile.student_id = '123456'
        self.user.userprofile.organization = settings.LOCAL_ORGANIZATION
        self.user.userprofile.save()

        self.student = User(username="student") # enrolled in the course
        self.student.set_password("student")
        self.student.save()
        self.student.userprofile.student_id = '654321'
        self.student.userprofile.organization = settings.LOCAL_ORGANIZATION
        self.student.userprofile.save()

        self.course = Course.objects.create(
            name="Test course",
            code="123456",
            url="Course-Url",
        )

        self.today = timezone.now()
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.tomorrow + timedelta(days=1)
        self.yesterday = self.today - timedelta(days=1)

        # course instances with different view_access_to settings
        self.public_course_instance = CourseInstance.objects.create(
            instance_name="Public",
            starting_time=self.yesterday,
            ending_time=self.tomorrow,
            course=self.course,
            url="public",
            view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.INTERNAL_USERS,
        )

        self.all_regist_course_instance = CourseInstance.objects.create(
            instance_name="All registered users",
            starting_time=self.yesterday,
            ending_time=self.tomorrow,
            course=self.course,
            url="allregistered",
            view_content_to=CourseInstance.VIEW_ACCESS.ALL_REGISTERED,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.INTERNAL_USERS,
        )

        self.enroll_audience_course_instance = CourseInstance.objects.create(
            instance_name="Enrollment audience",
            starting_time=self.yesterday,
            ending_time=self.two_days_from_now,
            course=self.course,
            url="enrollmentaudience",
            view_content_to=CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.INTERNAL_USERS,
        )

        self.enrolled_course_instance = CourseInstance.objects.create(
            instance_name="Enrolled",
            starting_time=self.yesterday,
            ending_time=self.two_days_from_now,
            course=self.course,
            url="enrolled",
            view_content_to=CourseInstance.VIEW_ACCESS.ENROLLED,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.INTERNAL_USERS,
        )
        self.course_instances = [self.public_course_instance, self.all_regist_course_instance,
            self.enroll_audience_course_instance, self.enrolled_course_instance]

        # enrollment
        for instance in self.course_instances:
            instance.enroll_student(self.student)

        # module/exercise round for each course instance
        self.course_modules = {}
        for instance in self.course_instances:
            self.course_modules[instance.id] = CourseModule.objects.create(
                name="Test module",
                url="test-module",
                points_to_pass=10,
                course_instance=instance,
                opening_time=self.today,
                closing_time=self.tomorrow,
            )

        # category
        self.categories = {}
        for instance in self.course_instances:
            self.categories[instance.id] = LearningObjectCategory.objects.create(
                name="Test category",
                course_instance=instance,
                points_to_pass=0,
            )

        # learning objects
        self.learning_objects = {}
        for instance in self.course_instances:
            lobjects = []
            chapter = CourseChapter.objects.create(
                name="Test chapter",
                course_module=self.course_modules[instance.id],
                category=self.categories[instance.id],
                url='chapter1',
            )
            lobjects.append(chapter)
            lobjects.append(BaseExercise.objects.create(
                name="Embedded exercise",
                parent=chapter,
                status=LearningObject.STATUS.UNLISTED,
                course_module=self.course_modules[instance.id],
                category=self.categories[instance.id],
                url='embedexercise',
                max_submissions=10,
                max_points=10,
                points_to_pass=0,
            ))
            lobjects.append(BaseExercise.objects.create(
                name="Normal exercise",
                course_module=self.course_modules[instance.id],
                category=self.categories[instance.id],
                url='normalexercise',
                max_submissions=10,
                max_points=10,
                points_to_pass=0,
            ))
            self.learning_objects[instance.id] = lobjects

        # submissions
        self.submissions = {}
        for _course_instance_id, exercises in self.learning_objects.items():
            for exercise in exercises:
                if not exercise.is_submittable:
                    continue
                self.submissions[exercise.id] = []
                submission = Submission.objects.create(
                    exercise=exercise,
                )
                submission.submitters.add(self.student.userprofile)
                self.submissions[exercise.id].append(submission)

        # disable all logging
        logging.disable(logging.CRITICAL)

    def test_redirect_to_enroll(self):
        url = self.enrolled_course_instance.get_absolute_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)

        # unenrolled logged-in user should be redirected to the enroll page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertRedirects(response, self.enrolled_course_instance.get_url('enroll'))
        self.client.logout()

        # enrolled students should open the course front page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_course_home(self):
        url = self.enroll_audience_course_instance.get_absolute_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should see the course home page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the course front page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # course instance: all registered/logged-in users may see the course
        url = self.all_regist_course_instance.get_absolute_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should see the course home page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the course front page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # public course instance
        url = self.public_course_instance.get_absolute_url()
        # anonymous user should see the course front page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # unenrolled logged-in user should see the course home page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the course front page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # course content visible to the enrollment audience, but user is
        # not in the enrollment audience
        ext_instance = CourseInstance.objects.create(
            instance_name="Enrollment audience external",
            starting_time=self.yesterday,
            ending_time=self.tomorrow,
            course=self.course,
            url="extaudience",
            view_content_to=CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.EXTERNAL_USERS,
        )
        url = ext_instance.get_absolute_url()
        self.assertTrue(self.client.login(username=self.user.username, password="testUser"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # Forbidden
        response = self.client.get(ext_instance.get_url('enroll'))
        self.assertEqual(response.status_code, 200) # allowed to see the enrollment page
        response = self.client.post(ext_instance.get_url('enroll'))
        self.assertEqual(response.status_code, 403) # may not enroll
        self.client.logout()

        # course content visible to registered users (logged-in users), but user is
        # not in the enrollment audience
        ext_regist_instance = CourseInstance.objects.create( # noqa: F841
            instance_name="Enrollment audience external - view registered users",
            starting_time=self.yesterday,
            ending_time=self.tomorrow,
            course=self.course,
            url="extaudience-registusers",
            view_content_to=CourseInstance.VIEW_ACCESS.ALL_REGISTERED,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.EXTERNAL_USERS,
        )
        url = ext_instance.get_absolute_url()
        self.assertTrue(self.client.login(username=self.user.username, password="testUser"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # Forbidden
        response = self.client.get(ext_instance.get_url('enroll'))
        self.assertEqual(response.status_code, 200) # allowed to see the enrollment page
        response = self.client.post(ext_instance.get_url('enroll'))
        self.assertEqual(response.status_code, 403) # may not enroll
        self.client.logout()

    def test_course_module(self):
        url = self.course_modules[self.enrolled_course_instance.id].get_absolute_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should be redirected to enrollment page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertRedirects(response, self.enrolled_course_instance.get_url('enroll'))
        self.client.logout()
        # enrolled students should open the course module page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # course instance: access to enrollment audience (logged-in internal users)
        url = self.course_modules[self.enroll_audience_course_instance.id].get_absolute_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should see the module page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the course module page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # course instance: access to registered users (any logged-in users)
        url = self.course_modules[self.all_regist_course_instance.id].get_absolute_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should see the module page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the course module page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # course instance: access to anyone (anonymous)
        url = self.course_modules[self.public_course_instance.id].get_absolute_url()
        # anonymous user can open the module page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # unenrolled logged-in user should see the module page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the course module page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # course content visible to the enrollment audience, but user is
        # not in the enrollment audience
        ext_instance = CourseInstance.objects.create(
            instance_name="Enrollment audience external",
            starting_time=self.yesterday,
            ending_time=self.tomorrow,
            course=self.course,
            url="extaudience",
            view_content_to=CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.EXTERNAL_USERS,
        )
        ext_module = CourseModule.objects.create(
            name="Test module",
            url="test-module",
            points_to_pass=10,
            course_instance=ext_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
        )
        url = ext_module.get_absolute_url()
        self.assertTrue(self.client.login(username=self.user.username, password="testUser"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # Forbidden
        self.client.logout()

    def test_chapter_enrolled_only(self):
        url = self.learning_objects[self.enrolled_course_instance.id][0].get_display_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should be redirected to enrollment page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertRedirects(response, self.enrolled_course_instance.get_url('enroll'))
        self.client.logout()
        # enrolled students should open the chapter page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # chapter exercise
        chapter_exercise = self.learning_objects[self.enrolled_course_instance.id][1] # noqa: F841
        url = '/Course-Url/enrolled/test-module/chapter1/embedexercise/plain/'
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should be redirected to enrollment page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertRedirects(response, self.enrolled_course_instance.get_url('enroll'))
        self.client.logout()
        # enrolled students should open the chapter page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # normal exercise (not inside chapter)
        exercise = self.learning_objects[self.enrolled_course_instance.id][2]
        url = reverse('exercise', kwargs={
            'exercise_path': exercise.url,
            'module_slug': exercise.course_module.url,
            'instance_slug': exercise.course_module.course_instance.url,
            'course_slug': exercise.course_module.course_instance.course.url,
        })
        self.assertEqual(url, '/Course-Url/enrolled/test-module/normalexercise/')
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should be redirected to enrollment page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertRedirects(response, self.enrolled_course_instance.get_url('enroll'))
        self.client.logout()
        # enrolled students should open the chapter page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_chapter_enroll_audience(self):
        url = self.learning_objects[self.enroll_audience_course_instance.id][0].get_display_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in internal user should see the chapter page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the chapter page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # chapter exercise
        chapter_exercise = self.learning_objects[self.enroll_audience_course_instance.id][1] # noqa: F841
        url = '/Course-Url/enrollmentaudience/test-module/chapter1/embedexercise/plain/'
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in internal user should see the exercise
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the chapter page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # normal exercise (not inside chapter)
        exercise = self.learning_objects[self.enroll_audience_course_instance.id][2]
        url = reverse('exercise', kwargs={
            'exercise_path': exercise.url,
            'module_slug': exercise.course_module.url,
            'instance_slug': exercise.course_module.course_instance.url,
            'course_slug': exercise.course_module.course_instance.course.url,
        })
        self.assertEqual(url, '/Course-Url/enrollmentaudience/test-module/normalexercise/')
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should see the exercise
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the exercise page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # course content visible to the enrollment audience, but user is
        # not in the enrollment audience
        ext_instance = CourseInstance.objects.create(
            instance_name="Enrollment audience external",
            starting_time=self.yesterday,
            ending_time=self.tomorrow,
            course=self.course,
            url="extaudience",
            view_content_to=CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.EXTERNAL_USERS,
        )
        ext_module = CourseModule.objects.create(
            name="Test module",
            url="test-module",
            points_to_pass=10,
            course_instance=ext_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
        )
        ext_category = LearningObjectCategory.objects.create(
            name="External test category",
            course_instance=ext_instance,
            points_to_pass=0,
        )
        ext_chapter = CourseChapter.objects.create(
            name="External test chapter",
            course_module=ext_module,
            category=ext_category,
            url='extchapter1',
        )
        url = ext_chapter.get_display_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in internal user should NOT see the chapter page
        # (user is not external and the course is visible to external users only)
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()

    def test_chapter_all_registered(self):
        url = self.learning_objects[self.all_regist_course_instance.id][0].get_display_url()
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in internal user should see the chapter page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the chapter page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # chapter exercise
        chapter_exercise = self.learning_objects[self.all_regist_course_instance.id][1] # noqa: F841
        url = '/Course-Url/allregistered/test-module/chapter1/embedexercise/plain/'
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in internal user should see the exercise
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the chapter page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # normal exercise (not inside chapter)
        exercise = self.learning_objects[self.all_regist_course_instance.id][2]
        url = reverse('exercise', kwargs={
            'exercise_path': exercise.url,
            'module_slug': exercise.course_module.url,
            'instance_slug': exercise.course_module.course_instance.url,
            'course_slug': exercise.course_module.course_instance.course.url,
        })
        self.assertEqual(url, '/Course-Url/allregistered/test-module/normalexercise/')
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should see the exercise
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the exercise page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_chapter_public(self):
        url = self.learning_objects[self.public_course_instance.id][0].get_display_url()
        # anonymous user can open the chapter
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # unenrolled logged-in internal user should see the chapter page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the chapter page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # chapter exercise
        chapter_exercise = self.learning_objects[self.public_course_instance.id][1] # noqa: F841
        url = '/Course-Url/public/test-module/chapter1/embedexercise/plain/'
        # anonymous user can open the chapter exercise
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # unenrolled logged-in internal user should see the exercise
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the chapter exercise normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # normal exercise (not inside chapter)
        exercise = self.learning_objects[self.public_course_instance.id][2]
        url = reverse('exercise', kwargs={
            'exercise_path': exercise.url,
            'module_slug': exercise.course_module.url,
            'instance_slug': exercise.course_module.course_instance.url,
            'course_slug': exercise.course_module.course_instance.course.url,
        })
        self.assertEqual(url, '/Course-Url/public/test-module/normalexercise/')
        # anonymous user can open the exercise
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # unenrolled logged-in user should see the exercise
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        # enrolled students should open the exercise page normally
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_submission(self):
        # submission in the chapter exercise
        chapter_exercise = self.learning_objects[self.enrolled_course_instance.id][1]
        submission = self.submissions[chapter_exercise.id][0]
        url = submission.get_absolute_url()
        self.assertEqual(url,
            '/Course-Url/enrolled/test-module/chapter1/embedexercise/submissions/{0}/'.format(
                submission.id))
        # should redirect to A+ login
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        # unenrolled logged-in user should be redirected to enrollment page
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertRedirects(response, self.enrolled_course_instance.get_url('enroll'))
        self.client.logout()
        # enrolled non-submitter user should not see the submission
        self.enrolled_course_instance.enroll_student(self.user)
        self.assertTrue(self.client.login(username=self.user.username, password='testUser'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()
        self.enrolled_course_instance.get_enrollment_for(self.user).delete()
        # the submitter should see her submission
        self.assertTrue(self.client.login(username=self.student.username, password="student"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_enroll(self):
        self.assertTrue(self.enrolled_course_instance.is_enrollable(self.user))
        self.assertTrue(self.enrolled_course_instance.is_enrollment_open())

        # course instance is hidden from students
        new_instance = CourseInstance.objects.create(
            instance_name="Hidden course instance",
            starting_time=self.yesterday,
            ending_time=self.tomorrow,
            course=self.course,
            url="hiddencourse",
            view_content_to=CourseInstance.VIEW_ACCESS.PUBLIC,
            enrollment_audience=CourseInstance.ENROLLMENT_AUDIENCE.INTERNAL_USERS,
            visible_to_students=False,
        )
        url = new_instance.get_url('enroll')
        # anonymous user accesses a hidden course: redirect to login
        response = self.client.post(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)

        # enrollment closed
        new_instance.visible_to_students = True
        new_instance.enrollment_starting_time = self.yesterday
        new_instance.enrollment_ending_time = self.yesterday + timedelta(hours=1)
        new_instance.save()
        url = new_instance.get_url('enroll')
        self.assertTrue(new_instance.is_enrollable(self.user))
        self.assertFalse(new_instance.is_enrollment_open())
        self.assertTrue(self.client.login(username=self.user.username, password="testUser"))
        response = self.client.get(url)
        # can open the enrollment page
        self.assertEqual(response.status_code, 200)
        # can not enroll
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()

    def test_enrollment_exercise(self):
        instance = self.enrolled_course_instance
        enroll_exercise = self.learning_objects[instance.id][2]
        enroll_exercise.status = LearningObject.STATUS.ENROLLMENT
        enroll_exercise.save()
        enroll_url = instance.get_url('enroll')
        exercise_url = reverse('exercise', kwargs={
            'exercise_path': enroll_exercise.url,
            'module_slug': enroll_exercise.course_module.url,
            'instance_slug': enroll_exercise.course_module.course_instance.url,
            'course_slug': enroll_exercise.course_module.course_instance.course.url,
        })

        # anonymous may not open the exercise nor enroll
        response = self.client.post(enroll_url)
        self.assertRedirects(response, '/accounts/login/?next=' + enroll_url)
        response = self.client.get(exercise_url)
        self.assertRedirects(response, '/accounts/login/?next=' + exercise_url)
        response = self.client.post(exercise_url)
        self.assertRedirects(response, '/accounts/login/?next=' + exercise_url)
        # the course has only one enrollment (made in setUp())
        self.assertEqual(instance.students.count(), 1)

        # logged-in user may open the exercise and submit
        self.assertTrue(self.client.login(username=self.user.username, password="testUser"))
        response = self.client.post(enroll_url)
        self.assertRedirects(response, exercise_url) # redirects to the enrollment exercise
        response = self.client.get(exercise_url)
        self.assertEqual(response.status_code, 200)
        # Since there is no exercise service running in the unit test environment,
        # we can not make test submissions to the exercise.
        success_flag, warnings, _students = enroll_exercise.check_submission_allowed(self.user.userprofile)
        self.assertEqual(success_flag, BaseExercise.SUBMIT_STATUS.ALLOWED)
        self.assertEqual(len(warnings), 0)
        instance.enroll_student(self.user)
        self.assertEqual(instance.students.count(), 2)
        self.assertTrue(instance.is_student(self.user))
        self.client.logout()

    def test_enrollment_exercise_external_users(self):
        # only external users may enroll
        instance = self.enrolled_course_instance
        instance.enrollment_audience = CourseInstance.ENROLLMENT_AUDIENCE.EXTERNAL_USERS
        instance.save()

        enroll_exercise = self.learning_objects[instance.id][2]
        enroll_exercise.status = LearningObject.STATUS.ENROLLMENT_EXTERNAL
        enroll_exercise.save()
        enroll_url = instance.get_url('enroll')
        exercise_url = reverse('exercise', kwargs={
            'exercise_path': enroll_exercise.url,
            'module_slug': enroll_exercise.course_module.url,
            'instance_slug': enroll_exercise.course_module.course_instance.url,
            'course_slug': enroll_exercise.course_module.course_instance.course.url,
        })

        # internal user may not enroll
        self.assertTrue(self.client.login(username=self.user.username, password="testUser"))
        response = self.client.post(enroll_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(exercise_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(exercise_url)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(instance.is_student(self.user))
        self.client.logout()

    def tearDown(self):
        # return previous logging settings
        logging.disable(logging.NOTSET)
