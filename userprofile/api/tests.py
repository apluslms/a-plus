from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

class UserProfileAPITest(TestCase):
    # use same setUp as for normal tests
    from ..tests import UserProfileTest
    setUp = UserProfileTest.setUp

    def test_rest_userlist(self):
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
                {'url': 'http://testserver/api/v2/users/1/',
                 'first_name': 'Superb',
                 'user_id': 1,
                 'username': 'testUser',
                 'student_id': '12345X',
                 'email': 'test@aplus.com',
                 'last_name': 'Student'},
                {'url': 'http://testserver/api/v2/users/2/',
                 'first_name': 'Grumpy',
                 'user_id': 2,
                 'username': 'grader',
                 'student_id': '67890Y',
                 'email': 'grader@aplus.com',
                 'last_name': 'Grader'},
                {'url': 'http://testserver/api/v2/users/3/',
                 'first_name': 'Tedious',
                 'user_id': 3,
                 'username': 'teacher',
                 'student_id': None,
                 'email': 'teacher@aplus.com',
                 'last_name': 'Teacher'},
                {'url': 'http://testserver/api/v2/users/4/',
                 'first_name': 'Super',
                 'user_id': 4,
                 'username': 'superuser',
                 'student_id': None,
                 'email': 'superuser@aplus.com',
                 'last_name': 'User'}
                ]
            })

    def test_rest_singleuser(self):
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get('/api/v2/users/1/')
        self.assertEqual(response.data, {
            'url': 'http://testserver/api/v2/users/1/',
            'user_id': 1,
            'student_id':'12345X',
            'username':'testUser',
            'first_name':'Superb',
            'last_name':'Student',
            'email':'test@aplus.com'})
