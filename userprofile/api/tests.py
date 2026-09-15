from typing import Set
from rest_framework.test import APIClient
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
