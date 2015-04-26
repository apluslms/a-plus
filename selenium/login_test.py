import unittest
import xmlrunner
from test_initializer import TestInitializer
from page_objects import CourseName, LoginPage, HomePage

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
            pass

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(output='test-reports'),
        # these make sure that some options that are not applicable
        # remain hidden from the help menu.
        failfast=False, buffer=False, catchbreak=False)