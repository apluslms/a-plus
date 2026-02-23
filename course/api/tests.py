from django.test import override_settings
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from course.models import CourseInstance
from ..tests import CourseTestCase

class CourseInstanceAPITest(CourseTestCase):
    # uses the same setUpTestData as for normal tests

    @override_settings(BASE_URL="http://testserver/")
    def test_get_courselist(self):
        """
        Test if list of courses are given correctly via REST.
        This does not need any authentication.
        """
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get('/api/v2/courses/')

        model = {
            'count': 4,
            'next': None,
            'previous': None,
        }

        for key in model: # pylint: disable=consider-using-dict-items
            with self.subTest(key=key):
                self.assertIn(key, response.data)
                self.assertEqual(response.data[key], model[key])

        results = [
            {
                'id': 1,
                'url': 'http://testserver/api/v2/courses/1',
                'html_url': 'http://testserver/Course-Url/T-00.1000_d0/',
                'code': '123456',
                'name': 'test course',
                'instance_name': 'Fall 2011 day 0'
            },
            {
                'id': 2,
                'url': 'http://testserver/api/v2/courses/2',
                'html_url': 'http://testserver/Course-Url/T-00.1000_d1/',
                'code': '123456',
                'name': 'test course',
                'instance_name': 'Fall 2011 day 1'
            },
            {
                'id': 3,
                'url': 'http://testserver/api/v2/courses/3',
                'html_url': 'http://testserver/Course-Url/T-00.1000_d2/',
                'code': '123456',
                'name': 'test course',
                'instance_name': 'Fall 2011 day 2'
            },
            {
                'id': 4,
                'url': 'http://testserver/api/v2/courses/4',
                'html_url': 'http://testserver/Course-Url/T-00.1000_hidden/',
                'code': '123456',
                'name': 'test course',
                'instance_name': 'Secret super course'
            },
        ]

        self.assertIn('results', response.data)
        r = response.data['results']
        self.assertEqual(len(r), len(results), "Wrong number of results")
        for course in results:
            with self.subTest(id=course['id'], course=course):
                u = next((u for u in r if u.get('id') == course['id']), None)
                self.assertNotEqual(u, None, "Course with id %s not found from the result list" % (course['id'],))
                u = dict(u) # convert OrderedDict to dict for more clear error messages
                self.assertDictEqual(u, course)

        # check that there is no extra fields
        model['results'] = results
        self.assertCountEqual(response.data, model)

    def test_post_course(self):
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.post(
            "/api/v2/courses/",
            {
                "code": "CS-TEST",
                "name": "TestiCourse",
                "course_url": "cstest",
                "instance_name": "Fall 2021",
                "url": "fall2021",
                "language": "en",
                "starting_time": "2022-01-01T12:00",
                "ending_time": "2022-05-31T12:00",
                "visible_to_students": False,
                "configure_url": "https://grader.cs.aalto.fi/test/url/",
                "teachers": [
                    "staff",
                    "newteacher"
                ]
            },
            format='json'
        )
        data = response.data
        self.assertEqual(data['id'], 5)

        course = CourseInstance.objects.get(id=5)
        self.assertEqual(course.instance_name, "Fall 2021")
        self.assertEqual(course.url, "fall2021")

        t = map(lambda x: x.user.username, course.teachers)
        self.assertIn('staff', t)
        self.assertIn('newteacher', t)

    def test_put_course(self):
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.put(
            "/api/v2/courses/2/",
            {
                "code": "123456",
                "name": "test course",
                "course_url": "Course-Url",
                "instance_name": "Fall 2011 day 1 fixed",
                "url": "T-00.1000_d0-fixed",
                "language": "en",
                "starting_time": "2022-01-01T12:00",
                "ending_time": "2022-05-31T12:00",
                "visible_to_students": False,
                "configure_url": "https://grader.cs.aalto.fi/test/url/",
                "teachers": [
                    "staff",
                    "newteacher"
                ]
            },
            format='json'
        )
        data = response.data
        self.assertEqual(data['id'], 2)

        course = CourseInstance.objects.get(id=2)
        self.assertEqual(course.instance_name, "Fall 2011 day 1 fixed")
        self.assertEqual(course.url, "T-00.1000_d0-fixed")

        t = map(lambda x: x.user.username, course.teachers)
        self.assertIn('staff', t)
        self.assertIn('newteacher', t)

    def test_get_current_teachers(self):
        self.user.email = 'teacher1@example.com'
        self.user.save(update_fields=['email'])
        self.user1.email = 'teacher2@example.com'
        self.user1.save(update_fields=['email'])
        self.user2.email = 'pastteacher@example.com'
        self.user2.save(update_fields=['email'])

        self.current_course_instance.add_teacher(self.user.userprofile)
        self.current_course_instance.add_teacher(self.user1.userprofile)
        self.future_course_instance.add_teacher(self.user1.userprofile)
        self.past_course_instance.add_teacher(self.user2.userprofile)

        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get('/api/v2/courses/current-teachers/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

        results = response.data['results']
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(results), 2)

        emails = sorted(row['email'] for row in results)
        self.assertEqual(emails, ['teacher1@example.com', 'teacher2@example.com'])

    def test_get_current_teachers_requires_permission(self):
        self.current_course_instance.add_teacher(self.user.userprofile)

        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get('/api/v2/courses/current-teachers/')
        self.assertEqual(response.status_code, 403)

    def test_get_current_teachers_with_permission(self):
        self.current_course_instance.add_teacher(self.user1.userprofile)
        self.user1.email = 'teacher2@example.com'
        self.user1.save(update_fields=['email'])

        permission = Permission.objects.get(
            content_type__app_label='course',
            codename='view_current_teachers',
        )
        self.user.user_permissions.add(permission)

        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get('/api/v2/courses/current-teachers/')

        self.assertEqual(response.status_code, 200)
        emails = [row['email'] for row in response.data['results']]
        self.assertIn('teacher2@example.com', emails)

    def test_get_current_teachers_ended_within_days(self):
        self.user.email = 'teacher1@example.com'
        self.user.save(update_fields=['email'])
        self.user2.email = 'pastteacher@example.com'
        self.user2.save(update_fields=['email'])

        self.current_course_instance.add_teacher(self.user.userprofile)
        self.past_course_instance.add_teacher(self.user2.userprofile)

        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get('/api/v2/courses/current-teachers/?ended_within_days=365')

        self.assertEqual(response.status_code, 200)
        emails = sorted(row['email'] for row in response.data['results'])
        self.assertEqual(emails, ['pastteacher@example.com', 'teacher1@example.com'])

    def test_get_current_teachers_ended_within_days_invalid(self):
        client = APIClient()
        client.force_authenticate(user=self.superuser)

        response = client.get('/api/v2/courses/current-teachers/?ended_within_days=abc')
        self.assertEqual(response.status_code, 400)

        response = client.get('/api/v2/courses/current-teachers/?ended_within_days=-1')
        self.assertEqual(response.status_code, 400)
