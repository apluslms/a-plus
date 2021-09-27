from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from course.models import CourseInstance

class CourseInstanceAPITest(TestCase):
    # use same setUp as for normal tests
    from ..tests import CourseTest
    setUp = CourseTest.setUp

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

        for key in model:
            with self.subTest(key=key):
                self.assertIn(key, response.data)
                self.assertEqual(response.data[key], model[key])

        results = [
            {
                'id': 1,
                'url': 'http://testserver/api/v2/courses/1/',
                'html_url': 'http://testserver/Course-Url/T-00.1000_d0/',
                'code': '123456',
                'name': 'test course',
                'instance_name': 'Fall 2011 day 0'
            },
            {
                'id': 2,
                'url': 'http://testserver/api/v2/courses/2/',
                'html_url': 'http://testserver/Course-Url/T-00.1000_d1/',
                'code': '123456',
                'name': 'test course',
                'instance_name': 'Fall 2011 day 1'
            },
            {
                'id': 3,
                'url': 'http://testserver/api/v2/courses/3/',
                'html_url': 'http://testserver/Course-Url/T-00.1000_d2/',
                'code': '123456',
                'name': 'test course',
                'instance_name': 'Fall 2011 day 2'
            },
            {
                'id': 4,
                'url': 'http://testserver/api/v2/courses/4/',
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
