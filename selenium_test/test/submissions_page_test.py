import unittest

from test_initializer import TestInitializer
from page_objects import LoginPage, MyFirstExerciseGrader, MyAjaxExerciseGrader, SubmissionPage, CourseName


class SubmissionsPageTest(unittest.TestCase):

    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()
        TestInitializer().recreateDatabase()
        LoginPage(self.driver).loginAsAssistant()

    def testShouldContainAsManySubmissionsAsSubmitted(self):
        firstExercisePage = MyFirstExerciseGrader(self.driver)
        firstExercisePage.setText("123test")
        firstExercisePage.submit()
        self.assertEqual(SubmissionPage(self.driver, exerciseId="1").getSubmissionCount(), 1)

        firstExercisePage = MyFirstExerciseGrader(self.driver)
        firstExercisePage.setText("Hello")
        firstExercisePage.submit()
        self.assertEqual(SubmissionPage(self.driver, exerciseId="1").getSubmissionCount(), 2)

        ajaxExercisePage = MyAjaxExerciseGrader(self.driver)
        ajaxExercisePage.setText("-1")
        ajaxExercisePage.submit()
        self.assertEqual(SubmissionPage(self.driver, exerciseId="3").getSubmissionCount(), 1)

        ajaxExercisePage = MyAjaxExerciseGrader(self.driver)
        ajaxExercisePage.setText("50")
        ajaxExercisePage.submit()
        self.assertEqual(SubmissionPage(self.driver, exerciseId="3").getSubmissionCount(), 2)

        firstExercisePage = MyFirstExerciseGrader(self.driver)
        firstExercisePage.setText("HelloA+")
        firstExercisePage.submit()
        self.assertEqual(SubmissionPage(self.driver, exerciseId="1").getSubmissionCount(), 3)

        ajaxExercisePage = MyAjaxExerciseGrader(self.driver)
        ajaxExercisePage.setText("100")
        ajaxExercisePage.submit()
        self.assertEqual(SubmissionPage(self.driver, exerciseId="3").getSubmissionCount(), 3)

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
