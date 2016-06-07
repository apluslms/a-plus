from collections import OrderedDict
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
        response = client.get('/api/v2/users/')
        self.assertEqual(response.data, OrderedDict([
            ('count', 4), ('next', None), ('previous', None),
            ('results',
                [OrderedDict([
                    ('user', 'http://testserver/api/v2/users/1/'),
                    ('student_id', '12345X'),
                    ('username', 'testUser'),
                    ('first_name', 'Superb'),
                    ('last_name', 'Student'),
                    ('email', 'test@aplus.com'),
                ]), OrderedDict([
                    ('user', 'http://testserver/api/v2/users/2/'),
                    ('student_id', '67890Y'),
                    ('username', 'grader'),
                    ('first_name', 'Grumpy'),
                    ('last_name', 'Grader'),
                    ('email', 'grader@aplus.com'),
                ]), OrderedDict([
                    ('user', 'http://testserver/api/v2/users/3/'),
                    ('student_id', None),
                    ('username', 'teacher'),
                    ('first_name', 'Tedious'),
                    ('last_name', 'Teacher'),
                    ('email', 'teacher@aplus.com'),
                ]), OrderedDict([
                    ('user', 'http://testserver/api/v2/users/4/'),
                    ('student_id', None),
                    ('username', 'superuser'),
                    ('first_name', 'Super'),
                    ('last_name', 'User'),
                    ('email', 'superuser@aplus.com'),
                ])]
            )]))

    def test_rest_singleuser(self):
        client = APIClient()
        response = client.get('/api/v2/users/1/')
        self.assertEqual(response.data, {
            'user': 'http://testserver/api/v2/users/1/',
            'student_id':'12345X',
            'username':'testUser',
            'first_name':'Superb',
            'last_name':'Student',
            'email':'test@aplus.com'})
