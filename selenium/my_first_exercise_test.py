import unittest
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities

from page_objects import CourseName, LoginPage, MyFirstExerciseGrader
from locators import CourseLocators

class MyFirstExerciseTest(unittest.TestCase):
    def setUp(self):
        # Set up browser logging
        firefoxCapabilities =  DesiredCapabilities.FIREFOX
        firefoxCapabilities['loggingPrefs'] = {'Browser': 'ALL'}
        self.driver = webdriver.Firefox(capabilities=firefoxCapabilities)
        LoginPage(self.driver).loginToCourse(CourseName.APLUS)

    def testShouldGiveZeroPointsOnEmptyAnswer(self):
        exercisePage = MyFirstExerciseGrader(self.driver)
        exercisePage.setText("")
        exercisePage.submit()

        self.assertEqual(exercisePage.getAllowedSubmissions(), u'4/10')
        self.assertEqual(exercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(exercisePage.getNumberOfSubmitters(), '1')
        self.assertEqual(exercisePage.getAverageSubmissionsPerStudent(), u'4.00')

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)