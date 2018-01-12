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
        self.assertEqual(self.baseUrl, str(self.driver.current_url))
        basePage = BasePage(self.driver)
        self.assertTrue(basePage.isElementPresent(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertTrue(basePage.isElementPresent(StaffPageLocators.SUBMISSION_LINKS))
        basePage.clickTeachersViewLink()
        self.assertEqual(self.baseUrl + 'teachers/', str(self.driver.current_url))

    def testShouldHaveAssistantsPermissions(self):
        LoginPage(self.driver).loginAsAssistant()
        self.assertEqual(self.baseUrl, str(self.driver.current_url))
        basePage = BasePage(self.driver)
        self.assertFalse(basePage.isElementPresent(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertTrue(basePage.isElementPresent(StaffPageLocators.SUBMISSION_LINKS))

    def testShouldHaveStudentsPermissions(self):
        LoginPage(self.driver).loginAsStudent()
        self.assertEqual(self.baseUrl, str(self.driver.current_url))
        basePage = BasePage(self.driver)
        self.assertFalse(basePage.isElementPresent(BasePageLocators.TEACHERS_VIEW_LINK))
        self.assertFalse(basePage.isElementPresent(StaffPageLocators.SUBMISSION_LINKS))

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
