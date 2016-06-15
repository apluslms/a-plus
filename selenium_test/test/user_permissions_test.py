import unittest

from test_initializer import TestInitializer
from page_objects import BasePage, LoginPage, CourseName
from locators import BasePageLocators, StaffPageLocators


class UserPermissionsTest(unittest.TestCase):
    baseUrl = BasePage.base_url + "/aplus1/basic_instance/"

    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()

    def testShouldHaveTeachersPermissions(self):
        LoginPage(self.driver).loginAsTeacher()
        basePage = BasePage(self.driver)
        self.assertTrue(basePage.isElementVisible(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertTrue(basePage.isElementVisible(StaffPageLocators.SUBMISSION_LINKS))
        basePage.clickTeachersViewLink()
        self.assertEqual(self.baseUrl + 'teachers/', str(self.driver.current_url))

    def testShouldHaveAssistantsPermissions(self):
        LoginPage(self.driver).loginAsAssistant()
        basePage = BasePage(self.driver)
        self.assertFalse(basePage.isElementVisible(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertTrue(basePage.isElementVisible(StaffPageLocators.SUBMISSION_LINKS))

    def testShouldHaveStudentsPermissions(self):
        LoginPage(self.driver).loginAsStudent()
        basePage = BasePage(self.driver)
        self.assertFalse(basePage.isElementVisible(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertFalse(basePage.isElementVisible(StaffPageLocators.SUBMISSION_LINKS))

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
