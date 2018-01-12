import unittest

from test_initializer import TestInitializer
from page_objects import LoginPage, FileUploadGrader, AssessmentPage, SubmissionPage, HomePage, StudentFeedbackPage


class TeacherFeedbackTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()
        TestInitializer().recreateDatabase()

    def testStudentShouldGetFeedbackWithNotification(self):
        ASSISTANT_FEEDBACK_TEXT = "ASSISTANT_FEEDBACK"
        FEEDBACK_TEXT = "FEEDBACK"
        EXERCISE_NUMBER = "2"
        SUBMISSION_NUMBER = 1
        POINTS = "50"

        # Submit exercise
        LoginPage(self.driver).loginAsStudent()
        fileUploadGrader = FileUploadGrader(self.driver)
        fileUploadGrader.submit()
        fileUploadGrader.logout()

        # Check submissions
        LoginPage(self.driver).loginAsAssistant()
        submissionPage = SubmissionPage(self.driver, exerciseId=EXERCISE_NUMBER)
        self.assertEqual(submissionPage.getSubmissionCount(), 1)

        # Assess exercise
        assessmentPage = AssessmentPage(self.driver, exerciseId=EXERCISE_NUMBER, submissionNumber=SUBMISSION_NUMBER)
        assessmentPage.setAssistantFeedback(ASSISTANT_FEEDBACK_TEXT)
        assessmentPage.setFeedback(FEEDBACK_TEXT)
        assessmentPage.setPoints(POINTS)
        assessmentPage.submit()
        assessmentPage.logout()

        # Check that student receives the correct assessment and a notification of it
        LoginPage(self.driver).loginAsStudent()
        homePage = HomePage(self.driver)
        self.assertTrue(homePage.hasNewNotifications())

        studentFeedbackPage = StudentFeedbackPage(self.driver, exerciseId=EXERCISE_NUMBER, submissionNumber=SUBMISSION_NUMBER)
        self.assertEqual(studentFeedbackPage.getAssistantFeedbackText(), ASSISTANT_FEEDBACK_TEXT)
        self.assertEqual(studentFeedbackPage.getFeedbackText(), FEEDBACK_TEXT)
        self.assertEqual(FileUploadGrader(self.driver).getPoints(), POINTS)

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
