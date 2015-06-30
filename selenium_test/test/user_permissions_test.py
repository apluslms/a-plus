import unittest

from test_initializer import TestInitializer
from page_objects import BasePage, LoginPage, CourseName
from locators import BasePageLocators, StaffPageLocators


class UserPermissionsTest(unittest.TestCase):
    baseUrl = BasePage.base_url + "/aplus1/basic_instance/"

    def setUp(self):
        self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()

    def testShouldHaveTeachersPermissions(self):
        LoginPage(self.driver).loginToCourse(CourseName.APLUS, "teacher_user", "admin")
        basePage = BasePage(self.driver)
        self.assertTrue(basePage.isElementVisible(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertTrue(basePage.isElementVisible(StaffPageLocators.SUBMISSION_LINKS))
        #self.assertTrue(basePage.isElementVisible(BasePageLocators.ASSISTANTS_VIEW_LINK))
        basePage.clickTeachersViewLink()
        self.assertEqual(self.baseUrl + 'teachers/', str(self.driver.current_url))

    def testShouldHaveAssistantsPermissions(self):
        LoginPage(self.driver).loginToCourse(CourseName.APLUS, "assistant_user", "admin")
        basePage = BasePage(self.driver)
        self.assertFalse(basePage.isElementVisible(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertTrue(basePage.isElementVisible(StaffPageLocators.SUBMISSION_LINKS))
        #self.assertTrue(basePage.isElementVisible(BasePageLocators.ASSISTANTS_VIEW_LINK))
        #basePage.clickAssistantsViewLink()
        #self.assertEqual(self.baseUrl + 'assistants/', str(self.driver.current_url))

    def testShouldHaveStudentsPermissions(self):
        LoginPage(self.driver).loginToCourse(CourseName.APLUS, "student_user", "admin")
        basePage = BasePage(self.driver)
        self.assertFalse(basePage.isElementVisible(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertFalse(basePage.isElementVisible(StaffPageLocators.SUBMISSION_LINKS))
        #self.assertFalse(basePage.isElementVisible(BasePageLocators.ASSISTANTS_VIEW_LINK))

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)

