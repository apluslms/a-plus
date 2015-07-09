import unittest

from page_objects import LoginPage, MyAjaxExerciseGrader
from test_initializer import TestInitializer


class MyAjaxExerciseGraderTest(unittest.TestCase):
    def setUp(self):
        testInitializer = TestInitializer()
        self.driver = testInitializer.getFirefoxDriverWithLoggingEnabled()
        testInitializer.recreateDatabase()
        LoginPage(self.driver).loginAsStudent()

    def testShouldGiveZeroPointsOnEmptySubmit(self):
        myAjaxExercisePage = MyAjaxExerciseGrader(self.driver)
        myAjaxExercisePage.submit()
        myAjaxExercisePage.waitForAjax()
        self.assertEqual(myAjaxExercisePage.getAllowedSubmissions(), '1 / 10')
        self.assertEqual(myAjaxExercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(myAjaxExercisePage.getNumberOfSubmitters(), '1')
        #self.assertEqual(myAjaxExercisePage.getAverageSubmissionsPerStudent(), '1.00')

    def testShouldGiveGivenPoints(self):
        myAjaxExercisePage = MyAjaxExerciseGrader(self.driver)
        myAjaxExercisePage.setText("50")
        myAjaxExercisePage.submit()
        myAjaxExercisePage.waitForAjax()
        self.assertEqual(myAjaxExercisePage.getAllowedSubmissions(), '1 / 10')
        self.assertEqual(myAjaxExercisePage.getExerciseScore(), '50 / 100')
        self.assertEqual(myAjaxExercisePage.getNumberOfSubmitters(), '1')
        #self.assertEqual(myAjaxExercisePage.getAverageSubmissionsPerStudent(), '1.00')

    def testShouldGiveZeroPointsOnOverTheLimitSubmit(self):
        myAjaxExercisePage = MyAjaxExerciseGrader(self.driver)
        myAjaxExercisePage.setText("101")
        myAjaxExercisePage.submit()
        myAjaxExercisePage.waitForAjax()
        self.assertEqual(myAjaxExercisePage.getAllowedSubmissions(), '1 / 10')
        self.assertEqual(myAjaxExercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(myAjaxExercisePage.getNumberOfSubmitters(), '1')
        #self.assertEqual(myAjaxExercisePage.getAverageSubmissionsPerStudent(), '1.00')


    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
