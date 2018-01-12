import unittest

from test_initializer import TestInitializer
from page_objects import LoginPage, HomePage
from locators import BasePageLocators


class HomePageTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()
        TestInitializer().recreateDatabase()
        LoginPage(self.driver).loginAsStudent()

    def testInitialScoreShouldBeZero(self):
        self.assertEqual("0 / 300", HomePage(self.driver).getMainScore())

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
