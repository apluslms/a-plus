import time
import unittest

from test_initializer import TestInitializer
from page_objects import AbstractPage, CourseArchivePage
from locators import CourseArchiveLocators


class CourseArchivePageTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()

    def testApiDirectly(self):
        page = AbstractPage(self.driver)
        page.load("/api/v1/course/?format=json")
        data = page.getJSON()
        self.assertEqual(len(data["objects"]), 1)
        self.assertEqual(len(data["objects"][0]["instances"]), 2)

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
