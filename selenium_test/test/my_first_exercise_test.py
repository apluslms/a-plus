import unittest

from test_initializer import TestInitializer
from page_objects import LoginPage, MyFirstExerciseGrader


class MyFirstExerciseTest(unittest.TestCase):
    def setUp(self):
        testHelper = TestInitializer()
        testHelper.recreateDatabase()
        self.driver = testHelper.getFirefoxDriverWithLoggingEnabled()
        LoginPage(self.driver).loginAsStudent()

    def testShouldGiveZeroPointsOnEmptyAnswer(self):
        exercisePage = MyFirstExerciseGrader(self.driver)
        exercisePage.setText("")
        exercisePage.submit()

        self.assertEqual(exercisePage.getAllowedSubmissions(), '1 / 10')
        self.assertEqual(exercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(exercisePage.getNumberOfSubmitters(), '1')
        #self.assertEqual(exercisePage.getAverageSubmissionsPerStudent(), '1.00')

    def testShouldGiveZeroPointsOnTwoSubsequentWrongAnswers(self):
        exercisePage = MyFirstExerciseGrader(self.driver)
        exercisePage.setText("+A olleH")
        exercisePage.submit()
        exercisePage = MyFirstExerciseGrader(self.driver)
        exercisePage.setText("Hell+A")
        exercisePage.submit()

        self.assertEqual(exercisePage.getAllowedSubmissions(), '2 / 10')
        self.assertEqual(exercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(exercisePage.getNumberOfSubmitters(), '1')
        #self.assertEqual(exercisePage.getAverageSubmissionsPerStudent(), '2.00')

    def testShouldGiveHalfPoints(self):
        exercisePage = MyFirstExerciseGrader(self.driver)
        exercisePage.setText("A+ Hell")
        exercisePage.submit()

        self.assertEqual(exercisePage.getAllowedSubmissions(), '1 / 10')
        self.assertEqual(exercisePage.getExerciseScore(), '50 / 100')
        self.assertEqual(exercisePage.getNumberOfSubmitters(), '1')
        #self.assertEqual(exercisePage.getAverageSubmissionsPerStudent(), '1.00')

    def testShouldGiveFullPoints(self):
        exercisePage = MyFirstExerciseGrader(self.driver)
        exercisePage.setText("A+Hello")
        exercisePage.submit()

        self.assertEqual(exercisePage.getAllowedSubmissions(), '1 / 10')
        self.assertEqual(exercisePage.getExerciseScore(), '100 / 100')
        self.assertEqual(exercisePage.getNumberOfSubmitters(), '1')
        #self.assertEqual(exercisePage.getAverageSubmissionsPerStudent(), '1.00')

    def testShouldRejectAnswerIfMaxSubmissionsReached(self):
        i = 0
        maxSubmissions = 10;
        while (i <= maxSubmissions):
            exercisePage = MyFirstExerciseGrader(self.driver)
            exercisePage.submit()
            i += 1

        self.assertEqual(exercisePage.getAllowedSubmissions(), str(maxSubmissions) + ' / 10')
        self.assertEqual(exercisePage.getExerciseScore(), '0 / 100')
        self.assertEqual(exercisePage.getNumberOfSubmitters(), '1')
        #self.assertEqual(exercisePage.getAverageSubmissionsPerStudent(), str(maxSubmissions) + '.00')

    # This tests that after 3 submissions the 'My Submissions' dropdown contains also 3 elements
    def testSubmissionCount(self):
        i = 0
        maxSubmissions = 3
        while (i < maxSubmissions):
            exercisePage = MyFirstExerciseGrader(self.driver)
            exercisePage.submit()
            i += 1

        exercisePage = MyFirstExerciseGrader(self.driver)
        self.assertEqual(len(exercisePage.getMySubmissionsList()), 3)


    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
