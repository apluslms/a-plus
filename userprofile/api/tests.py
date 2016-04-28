from collections import OrderedDict
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from ..tests import UserProfileTest

class UserProfileAPITest(TestCase):
    # use same setUp as for normal tests
    setUp = UserProfileTest.setUp

    def test_rest_userlist(self):
        """
        Test if list of users are given correctly via REST.
        This does not need any authentication.
        """
        client = APIClient()
        response = client.get('/api/userprofile/')
        self.assertEqual(response.data, OrderedDict([('count', 4), ('next', None), ('previous', None), ('results',
        [OrderedDict([('user', 1), ('student_id', '12345X'), ('username', 'testUser'), ('first_name', 'Superb'), ('last_name', 'Student'), ('email', 'test@aplus.com')]),
         OrderedDict([('user', 2), ('student_id', '67890Y'), ('username', 'grader'), ('first_name', 'Grumpy'), ('last_name', 'Grader'), ('email', 'grader@aplus.com')]),
         OrderedDict([('user', 3), ('student_id', None), ('username', 'teacher'), ('first_name', 'Tedious'), ('last_name', 'Teacher'), ('email', 'teacher@aplus.com')]),
         OrderedDict([('user', 4), ('student_id', None), ('username', 'superuser'), ('first_name', 'Super'), ('last_name', 'User'), ('email', 'superuser@aplus.com')])])]))

    def test_rest_singleuser(self):
        client = APIClient()
        response = client.get('/api/userprofile/1/')
        self.assertEqual(response.data, {'user':1, 'student_id':'12345X', 'username':'testUser', 'first_name':'Superb', 'last_name':'Student', 'email':'test@aplus.com'})

    # TODO: Under construction
    # For testing API key authentication
    def test_update_user(self):
        token = Token.objects.get(user__username='superuser')
        client = APIClient()
        response = client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = client.put('/api/userprofile/4/', {'user':3, 'student_id':'987654', 'username':'teekkarit', 'first_name':'Teemu', 'last_name':'Teekkari', 'email':'teme@aplus.com'})
        print(response.data)
        self.assertEqual(response.data, "asdf")
