import unittest

from test_initializer import TestInitializer
from selenium_test.page_objects.page_objects import LoginPage, EditModulePage, CourseName


class EditModulePageTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getFirefoxDriverWithLoggingEnabled()
        TestInitializer().recreateDatabase()
        LoginPage(self.driver).loginToCourse(CourseName.APLUS)

    def testShouldSaveModule(self):
        courseName = "Testikurssi"
        pointsToPass = "10"
        openingTime = "2014-01-01 00:00:00"
        closingTime = "2016-01-01 00:00:00"

        editModulePage = EditModulePage(self.driver, 1)

        editModulePage.setCourseName(courseName)
        editModulePage.setPointsToPass(pointsToPass)
        editModulePage.setOpeningTime(openingTime)
        editModulePage.setClosingTime(closingTime)
        editModulePage.submit()

        self.assertTrue(editModulePage.isSuccessfulSave())

        editModulePage = EditModulePage(self.driver, 1)
        self.assertEqual(editModulePage.getCourseName(), courseName)
        self.assertEqual(editModulePage.getPointsToPass(), pointsToPass)
        self.assertEqual(editModulePage.getOpeningTime(), openingTime)
        self.assertEqual(editModulePage.getClosingTime(), closingTime)

    def tearDown(self):
        self.driver.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)