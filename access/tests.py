# -*- coding: utf-8 -*-
'''
This module holds unit tests. It has nothing to do with the grader tests.
'''
from django.conf import settings
from django.test import TestCase

from access.config import ConfigParser
from util.shell import invoke_script


class ConfigTestCase(TestCase):

    def setUp(self):
        self.config = ConfigParser()

    def test_parsing(self):
        from access.config import get_rst_as_html
        self.assertEqual(get_rst_as_html('A **foobar**.'), '<p>A <strong>foobar</strong>.</p>\n')
        import re
        from access.config import iterate_kvp_with_dfs
        data = {
            'title|i18n': {'en': 'A Title', 'fi': 'Eräs otsikko'},
            'text|rst': 'Some **fancy** text with ``links <http://google.com>`` and code like ``echo "moi"``.'
        }
        self.config._process_exercise_data({ "lang": "en" }, data)
        self.assertEqual(data["en"]["text"], data["fi"]["text"])
        self.assertEqual(data["en"]["title"], "A Title")
        self.assertEqual(data["fi"]["title"], "Eräs otsikko")

    def test_loading(self):
        courses = self.config.courses()
        self.assertGreater(len(courses), 0, "No courses configured")
        course_key = courses[0]["key"]

        root = self.config._course_root(course_key)
        ptime = root["ptime"]

        # Ptime changes if cache is missed.
        root = self.config._course_root(course_key)
        self.assertEqual(ptime, root["ptime"])

    def test_shell_invoke(self):
        r = invoke_script(settings.PREPARE_SCRIPT, {})
        self.assertEqual(1, r["code"])
        r = invoke_script(settings.PREPARE_SCRIPT, { "course_key": "foo", "dir": settings.SUBMISSION_PATH })
        self.assertEqual(0, r["code"])
