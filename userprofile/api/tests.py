from typing import Set

from aplus_auth.payload import Permission
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient

from authorization.object_permissions import ObjectPermissions
from course.models import CourseInstance, CourseModule, Enrollment
from exercise.models import BaseExercise, Submission
from lib.crypto import get_signed_message
from userprofile.models import GraderUser

from ..permissions import IsTeacherOrAdminOrSelf
from ..tests import UserProfileTestCase

class UserProfileAPITest(UserProfileTestCase):
    # use same setUp as for normal tests

    def test_get_userlist(self):
        """
        Test if list of users are given correctly via REST.
        This does not need any authentication.
        """
        client = APIClient()
        client.force_authenticate(user=self.superuser)

        results = [
            {
                'id': 101,
                'url': 'http://testserver/api/v2/users/101',
                'username': 'testUser',
                'student_id': '12345X',
                'email': 'test@aplus.com',
                'full_name': 'Superb Student',
                'is_external': False
            },
            {
                'id': 102,
                'url': 'http://testserver/api/v2/users/102',
                'username': 'grader',
                'student_id': '67890Y',
                'email': 'grader@aplus.com',
                'full_name': 'Grumpy Grader',
                'is_external': False
            },
            {
                'id': 103,
                'url': 'http://testserver/api/v2/users/103',
                'username': 'teacher',
                'student_id': None,
                'email': 'teacher@aplus.com',
                'full_name': 'Tedious Teacher',
                'is_external': True
            },
            {
                'id': 104,
                'url': 'http://testserver/api/v2/users/104',
                'username': 'superuser',
                'student_id': None,
                'email': 'superuser@aplus.com',
                'full_name': 'Super User',
                'is_external': True
            },
        ]

        for i, email in enumerate([result['email'] for result in results]):
            response = client.get(f'/api/v2/users/?search={email}')

            model = {
                'count': 1,
                'next': None,
                'previous': None,
            }

            for key in model: # pylint: disable=consider-using-dict-items
                with self.subTest(key=key):
                    self.assertIn(key, response.data)
                    self.assertEqual(response.data[key], model[key])

            self.assertIn('results', response.data)
            r = response.data['results']
            self.assertEqual(len(r), 1, "Wrong number of results")
            user = results[i]
            with self.subTest(id=user['id'], user=user):
                u = next((u for u in r if u.get('id') == user['id']), None)
                self.assertNotEqual(u, None, "User with id %s not found from the result list" % (user['id'],))
                u = dict(u) # convert OrderedDict to dict for more clear error messages
                self.assertDictEqual(u, user)

            # check that there is no extra fields
            model['results'] = results
            self.assertCountEqual(response.data, model)

    def test_get_userdetail(self):
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get('/api/v2/users/101/')
        self.assertEqual(response.data, {
            'id': 101,
            'url': 'http://testserver/api/v2/users/101',
            'username':'testUser',
            'student_id':'12345X',
            'is_external': False,
            'enrolled_courses': [],
            'staff_courses': [],
            'teacher_courses': [],
            'assistant_courses': [],
            'full_name':'Superb Student',
            'first_name':'Superb',
            'last_name':'Student',
            'email':'test@aplus.com',
        })

    def test_field_values_filter(self):
        client = APIClient()
        client.force_authenticate(user=self.superuser)

        # Helper function that checks that the response contains the expected user ids (and no others)
        def check_response(url: str, expected_ids: Set[int]) -> None:
            response = client.get(url)
            ids = {u['id'] for u in response.data['results']}
            self.assertSetEqual(ids, expected_ids)

        # Check that email field filter works
        check_response('/api/v2/users/?search=teacher@aplus.com', {103})

        # Check that unmatched values don't cause errors
        check_response('/api/v2/users/?search=invalid@aplus.com', set())

        # Check that an empty or missing values list returns an empty result
        check_response('/api/v2/users/', set())


class GraderUserAPITest(UserProfileTestCase):
    """
    Grader authentication tokens must not grant admin access to the user API.
    Previously every GraderUser was considered an admin, which allowed any
    valid grader token (e.g. an exercise token visible in a grader page URL)
    to read every user profile via /api/v2/users/<user_id>/.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.course_module = CourseModule.objects.create(
            name="test module",
            url="test-module",
            points_to_pass=10,
            course_instance=cls.course_instance1,
            opening_time=cls.today,
            closing_time=cls.tomorrow,
        )
        cls.exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=cls.course_module,
            category=cls.learning_object_category1,
            url="b1",
        )
        # A submission by the student: its token grants access to the
        # student's profile but no one else's.
        cls.submission = Submission.objects.create(exercise=cls.exercise)
        cls.submission.submitters.add(cls.student.userprofile)

    def _submission_token(self):
        return "s{:x}.{}".format(self.submission.id, self.submission.hash)

    def _exercise_token(self, user):
        identifier = "{:s}.{:d}".format(str(user.id), self.exercise.id)
        return "e{:s}".format(get_signed_message(identifier).decode('ascii'))

    def test_submission_token_access(self):
        """
        A submission token grants access only to the profile of the user
        who submitted, not to other users.
        """
        client = APIClient()
        token = self._submission_token()
        # Student (the submitter) profile is accessible
        response = client.get(f'/api/v2/users/{self.student.id}/?token={token}')
        self.assertEqual(response.status_code, 200)
        # Other users' profiles must not be accessible
        for other in (self.grader, self.teacher, self.superuser):
            response = client.get(f'/api/v2/users/{other.id}/?token={token}')
            self.assertIn(response.status_code, (403, 404),
                f"User {other.id} should not be accessible with a submission token")

    def test_exercise_token_access(self):
        """
        An exercise token grants access only to the profile of the user it
        was issued for (the submitting user), not to other users.
        """
        client = APIClient()
        token = self._exercise_token(self.student)
        # The token's user is accessible, as the token allows creating a
        # submission on their behalf.
        response = client.get(f'/api/v2/users/{self.student.id}/?token={token}')
        self.assertEqual(response.status_code, 200)
        # Other users' profiles must not be accessible
        for other in (self.grader, self.teacher, self.superuser):
            response = client.get(f'/api/v2/users/{other.id}/?token={token}')
            self.assertIn(response.status_code, (403, 404),
                f"User {other.id} should not be accessible with an exercise token")

    def test_invalid_token_is_rejected(self):
        client = APIClient()
        response = client.get(f'/api/v2/users/{self.student.id}/?token=invalidtoken')
        self.assertIn(response.status_code, (401, 403))

    def test_write_only_permission_grants_no_read_access(self):
        """
        A grader with only WRITE access to a submission must not be allowed
        to read its submitters' user profiles. READ is required for that.
        """
        permissions = ObjectPermissions()
        permissions.submissions.add(Permission.WRITE, self.submission)
        grader_user = GraderUser("test_grader", permissions)

        client = APIClient()
        client.force_authenticate(user=grader_user)
        response = client.get(f'/api/v2/users/{self.student.id}/')
        self.assertIn(response.status_code, (403, 404),
            "WRITE-only submission access must not allow reading user profiles")

    def test_token_cannot_list_users(self):
        """
        A grader token must not allow listing or searching all users.
        """
        client = APIClient()
        token = self._submission_token()
        # Searching by another user's email must not reveal that user
        response = client.get(
            f'/api/v2/users/?search={self.teacher.email}&token={token}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(), {u['id'] for u in response.data['results']})
        # Even without a search the full list must not be exposed
        response = client.get(f'/api/v2/users/?token={token}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(), {u['id'] for u in response.data['results']})


class IsTeacherOrAdminOrSelfTest(UserProfileTestCase):
    """
    Tests for the is_super() decision paths of IsTeacherOrAdminOrSelf after
    the full-table scan was replaced with a single course-instances query.
    Each path must use exactly the expected number of database queries.
    """

    def setUp(self):
        self.permission = IsTeacherOrAdminOrSelf()

    def test_superuser_is_super_without_queries(self):
        # Handled by the base is_super (is_staff/is_superuser), so the
        # teacher lookup must not run any queries.
        with self.assertNumQueries(0):
            self.assertTrue(self.permission.is_super(self.superuser))

    def test_active_teacher_is_super_with_single_query(self):
        # The teacher has active teacher enrollments on both course
        # instances. Add extra instances to prove the query count does not
        # grow with the number of course instances in the database.
        for i in range(3):
            CourseInstance.objects.create(
                instance_name=f"Extra instance {i}",
                starting_time=self.today,
                ending_time=self.tomorrow,
                course=self.course,
                url=f"T-00.1000_extra_{i}",
            )
        with self.assertNumQueries(1):
            self.assertTrue(self.permission.is_super(self.teacher))

    def test_teacher_role_must_be_active(self):
        # A removed teacher enrollment must not grant super status.
        enrollment = Enrollment.objects.get(
            course_instance=self.course_instance1,
            user_profile=self.teacher_profile,
            role=Enrollment.ENROLLMENT_ROLE.TEACHER,
        )
        enrollment.status = Enrollment.ENROLLMENT_STATUS.REMOVED
        enrollment.save()
        # The enrollment on course_instance2 is still active, so remove it too.
        Enrollment.objects.filter(
            course_instance=self.course_instance2,
            user_profile=self.teacher_profile,
        ).update(status=Enrollment.ENROLLMENT_STATUS.REMOVED)
        with self.assertNumQueries(1):
            self.assertFalse(self.permission.is_super(self.teacher))

    def test_normal_user_is_not_super_with_single_query(self):
        with self.assertNumQueries(1):
            self.assertFalse(self.permission.is_super(self.student))

    def test_anonymous_user_is_not_super_without_queries(self):
        # The authentication guard must short-circuit before any query.
        with self.assertNumQueries(0):
            self.assertFalse(self.permission.is_super(AnonymousUser()))
        # Anonymous HTTP access must be denied without the teacher lookup.
        client = APIClient()
        response = client.get(f'/api/v2/users/{self.student.id}/')
        self.assertIn(response.status_code, (401, 403))

    def test_grader_user_is_not_super_without_queries(self):
        # GraderUser has no userprofile attribute, so a missing guard would
        # raise AttributeError here. The grader branch must return False
        # without touching the database.
        permissions = ObjectPermissions()
        permissions.submissions.add(Permission.READ, Submission.objects.create(
            exercise=BaseExercise.objects.create(
                name="test exercise",
                course_module=CourseModule.objects.create(
                    name="test module",
                    url="test-module",
                    points_to_pass=10,
                    course_instance=self.course_instance1,
                    opening_time=self.today,
                    closing_time=self.tomorrow,
                ),
                category=self.learning_object_category1,
                url="b1",
            )
        ))
        grader_user = GraderUser("test_grader", permissions)
        with self.assertNumQueries(0):
            self.assertFalse(self.permission.is_super(grader_user))

    def test_teacher_can_access_other_profiles_via_api(self):
        client = APIClient()
        client.force_authenticate(user=self.teacher)
        for other in (self.student, self.grader, self.superuser):
            response = client.get(f'/api/v2/users/{other.id}/')
            self.assertEqual(response.status_code, 200,
                f"Teacher should be able to read profile of user {other.id}")

    def test_normal_user_cannot_access_other_profiles_via_api(self):
        client = APIClient()
        client.force_authenticate(user=self.student)
        # Own profile is accessible ...
        response = client.get(f'/api/v2/users/{self.student.id}/')
        self.assertEqual(response.status_code, 200)
        # ... but other profiles are not.
        for other in (self.teacher, self.superuser):
            response = client.get(f'/api/v2/users/{other.id}/')
            self.assertIn(response.status_code, (403, 404),
                f"Normal user should not be able to read profile of user {other.id}")
