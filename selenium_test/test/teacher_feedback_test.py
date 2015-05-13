import unittest

from test_initializer import TestInitializer
from selenium_test.page_objects.page_objects import LoginPage, FileUploadGrader, AssessmentPage, SubmissionPage, StudentFeedbackPage
from selenium_test.locators.locators import BasePageLocators


class TeacherFeedbackTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()
        TestInitializer().recreateDatabase()

    def testStudentShouldGetTeacherFeedbackWithNotification(self):
        ASSISTANT_FEEDBACK_TEXT = "ASSISTANT_FEEDBACK"
        FEEDBACK_TEXT = "FEEDBACK"
        MODULE_NUMBER = 2
        SUBMISSION_NUMBER = 1
        POINTS = "50"

        # Submit exercise
        LoginPage(self.driver).loginAsStudent(self.driver)
        fileUploadGrader = FileUploadGrader(self.driver)
        fileUploadGrader.submit()
        fileUploadGrader.logout()

        # Check submissions
        LoginPage(self.driver).loginAsTeacher(self.driver)
        submissionPage = SubmissionPage(self.driver, MODULE_NUMBER)
        self.assertEqual(submissionPage.getSubmissionCount(), 1)

        # Assess exercise
        assessmentPage = AssessmentPage(self.driver, SUBMISSION_NUMBER)
        assessmentPage.setAssistantFeedback(ASSISTANT_FEEDBACK_TEXT)
        assessmentPage.setFeedback(FEEDBACK_TEXT)
        assessmentPage.setPoints(POINTS)
        assessmentPage.submit()
        assessmentPage.logout()

        # Check that student receives the correct assessment and a notification of it
        LoginPage(self.driver).loginAsStudent(self.driver)
        studentFeedbackPage = StudentFeedbackPage(self.driver, SUBMISSION_NUMBER)

        self.assertTrue(studentFeedbackPage.hasNewNotifications())
        self.assertEqual(studentFeedbackPage.getAssistantFeedbackText(), ASSISTANT_FEEDBACK_TEXT)
        self.assertEqual(studentFeedbackPage.getFeedbackText(), FEEDBACK_TEXT)
        self.assertEqual(FileUploadGrader(self.driver).getPoints(), POINTS)

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2, warnings='ignore')
