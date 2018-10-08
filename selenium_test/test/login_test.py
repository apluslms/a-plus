import unittest

from test_initializer import TestInitializer
from page_objects import CourseName, LoginPage, HomePage


class LoginTest(unittest.TestCase):
    logoutPageURI = '/accounts/logout'

    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()

    def testLoginToTestCourseInstance(self):
        LoginPage(self.driver).loginToCourse(CourseName.APLUS)
        homePage = HomePage(self.driver, CourseName.APLUS)
        self.assertEqual(homePage.getCourseBanner(), 'aplus-001 My test course')
        self.assertTrue(LoginPage.defaultFullname in homePage.getLoggedInText())

    def testLoginToExampleHookCourseInstance(self):
        LoginPage(self.driver).loginToCourse(CourseName.HOOK)
        homePage = HomePage(self.driver, CourseName.HOOK)
        self.assertEqual(homePage.getCourseBanner(), 'aplus-001 My test course')
        self.assertTrue(LoginPage.defaultFullname in homePage.getLoggedInText())

    def testShouldThrowTimeoutExceptionOnWrongCredentials(self):
        loginPage = LoginPage(self.driver)
        try:
            loginPage.loginToCourse(CourseName.APLUS, 'fake', 'password')
        except Exception:
            return
        self.fail("There should have been an exception")

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
