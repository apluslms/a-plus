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
                 'username': 'testUser'},
                {'id': 2,
                 'url': 'http://testserver/api/v2/users/2/',
                 'username': 'grader'},
                {'id': 3,
                 'url': 'http://testserver/api/v2/users/3/',
                 'username': 'teacher'},
                {'id': 4,
                 'url': 'http://testserver/api/v2/users/4/',
                 'username': 'superuser'}
                ]
            })

    def test_get_userdetail(self):
        client = APIClient()
        client.force_authenticate(user=self.superuser)
        response = client.get('/api/v2/users/1/')
        self.assertEqual(response.data, {
            'id': 1,
            'url': 'http://testserver/api/v2/users/1/',
            'student_id':'12345X',
            'enrolled_courses': [],
            'username':'testUser',
            'full_name':'Superb Student',
            'first_name':'Superb',
            'last_name':'Student',
            'email':'test@aplus.com'})
