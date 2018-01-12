import unittest

from page_objects import LoginPage, MyAjaxExerciseGrader
from test_initializer import TestInitializer


class MyAjaxExerciseGraderTest(unittest.TestCase):
    def setUp(self):
        testInitializer = TestInitializer()
        self.driver = testInitializer.getDefaultDriver()
        testInitializer.recreateDatabase()
        LoginPage(self.driver).loginAsStudent()

    def testShouldGiveZeroPointsOnEmptySubmit(self):
        myAjaxExercisePage = MyAjaxExerciseGrader(self.driver)
        myAjaxExercisePage.submit()
        self.assertEqual(myAjaxExercisePage.getAllowedSubmissions(), '1 / 10')
        self.assertEqual(myAjaxExercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(myAjaxExercisePage.getNumberOfSubmitters(), '1')

    def testShouldGiveGivenPoints(self):
        myAjaxExercisePage = MyAjaxExerciseGrader(self.driver)
        myAjaxExercisePage.setText("50")
        myAjaxExercisePage.submit()
        self.assertEqual(myAjaxExercisePage.getAllowedSubmissions(), '1 / 10')
        self.assertEqual(myAjaxExercisePage.getExerciseScore(), '50 / 100')
        self.assertEqual(myAjaxExercisePage.getNumberOfSubmitters(), '1')

    def testShouldGiveZeroPointsOnOverTheLimitSubmit(self):
        myAjaxExercisePage = MyAjaxExerciseGrader(self.driver)
        myAjaxExercisePage.setText("101")
        myAjaxExercisePage.submit()

        # Over the limit leaves submission to error state and does not count.
        self.assertEqual(myAjaxExercisePage.getAllowedSubmissions(), '0 / 10')
        self.assertEqual(myAjaxExercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(myAjaxExercisePage.getNumberOfSubmitters(), '1')

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
