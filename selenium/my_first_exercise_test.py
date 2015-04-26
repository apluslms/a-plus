import unittest
from test_helper import TestHelper
from page_objects import CourseName, LoginPage, MyFirstExerciseGrader

class MyFirstExerciseTest(unittest.TestCase):
    def setUp(self):
        testHelper = TestHelper()
        testHelper.recreateDatabase()
        self.driver = testHelper.getFirefoxDriverWithLoggingEnabled()
        LoginPage(self.driver).loginToCourse(CourseName.APLUS)

    def testShouldGiveZeroPointsOnEmptyAnswer(self):
        exercisePage = MyFirstExerciseGrader(self.driver)
        exercisePage.setText("")
        exercisePage.submit()

        self.assertEqual(exercisePage.getAllowedSubmissions(), '1/10')
        self.assertEqual(exercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(exercisePage.getNumberOfSubmitters(), '1')
        self.assertEqual(exercisePage.getAverageSubmissionsPerStudent(), '1.00')

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)