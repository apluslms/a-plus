from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

class UserProfileAPITest(TestCase):
    # use same setUp as for normal tests
    from ..tests import UserProfileTest
    setUp = UserProfileTest.setUp

    def test_get_userlist(self):
        """
        Test if list of users are given correctly via REST.
        This does not need any authentication.
        """
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get('/api/v2/users/')
        self.assertEqual(response.data, {
            'count': 4, 'next': None, 'previous': None,
            'results': [
                {'id': 1,
                 'url': 'http://testserver/api/v2/users/1/',
                 'username': 'testUser',
                 'student_id': '12345X',
                 'email': 'test@aplus.com',
                 'is_external': False},
                {'id': 2,
                 'url': 'http://testserver/api/v2/users/2/',
                 'username': 'grader',
                 'student_id': '67890Y',
                 'email': 'grader@aplus.com',
                 'is_external': False},
                {'id': 3,
                 'url': 'http://testserver/api/v2/users/3/',
                 'username': 'teacher',
                 'student_id': None,
                 'email': 'teacher@aplus.com',
                 'is_external': False},
                {'id': 4,
                 'url': 'http://testserver/api/v2/users/4/',
                 'username': 'superuser',
                 'student_id': None,
                 'email': 'superuser@aplus.com',
                 'is_external': False},
                ]
            })

    def test_get_userdetail(self):
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get('/api/v2/users/1/')
        self.assertEqual(response.data, {
            'id': 1,
            'url': 'http://testserver/api/v2/users/1/',
            'username':'testUser',
            'student_id':'12345X',
            'is_external': False,
            'enrolled_courses': [],
            'full_name':'Superb Student',
            'first_name':'Superb',
            'last_name':'Student',
            'email':'test@aplus.com'})
