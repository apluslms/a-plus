import unittest
from test_initializer import TestInitializer
from page_objects import CourseName, LoginPage

class LoginTest(unittest.TestCase):
    logoutPageURI = '/accounts/logout'

    def setUp(self):
       self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()

    def testLoginToTestCourseInstance(self):
        loginPage = LoginPage(self.driver)
        loginPage.loginToCourse(CourseName.APLUS)
        print LoginPage.defaultUsername + " - " + loginPage.getLoggedInUsername()
        self.assertTrue(LoginPage.defaultUsername in loginPage.getLoggedInUsername())
        loginPage.logout()
        self.assertTrue(self.logoutPageURI in self.driver.current_url)


    def testLoginToExampleHookCourseInstance(self):
        loginPage = LoginPage(self.driver)
        loginPage.loginToCourse(CourseName.HOOK)
        self.assertTrue(LoginPage.defaultUsername in loginPage.getLoggedInUsername())
        loginPage.logout()
        self.assertTrue(self.logoutPageURI in self.driver.current_url)

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)