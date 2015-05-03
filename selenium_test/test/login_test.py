import unittest
from selenium_test.test_initializer import TestInitializer
from selenium_test.page_objects.page_objects import CourseName, LoginPage, HomePage

class LoginTest(unittest.TestCase):
    logoutPageURI = '/accounts/logout'

    def setUp(self):
       self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()

    def testLoginToTestCourseInstance(self):
        loginPage = LoginPage(self.driver)
        loginPage.loginToCourse(CourseName.APLUS)
        homePage = HomePage(self.driver, CourseName.APLUS)
        self.assertEqual(homePage.getCourseBanner(), 'A+ Test Course Instance')


    def testLoginToExampleHookCourseInstance(self):
        loginPage = LoginPage(self.driver)
        loginPage.loginToCourse(CourseName.HOOK)
        homePage = HomePage(self.driver, CourseName.HOOK)
        self.assertEqual(homePage.getCourseBanner(), 'Hook Example')

    def testShouldThrowTimoutExceptionOnWrongCredentials(self):
        loginPage = LoginPage(self.driver)
        try:
            loginPage.loginToCourse(CourseName.APLUS, 'fake', 'password')
        except Exception:
            return

        self.fail("There should have been an exception")

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)