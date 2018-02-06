import unittest

from test_initializer import TestInitializer
from page_objects import LoginPage, EditModulePage, CourseName


class EditModulePageTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()
        TestInitializer().recreateDatabase()
        LoginPage(self.driver).loginAsTeacher()

    def testShouldSaveModule(self):
        COURSE_NAME = "Testikurssi"
        POINTS_TO_PASS = "10"
        OPENING_TIME = "2014-01-01 00:00:00"
        CLOSING_TIME = "2016-01-01 00:00:00"
        MODULE_ID = 1

        editModulePage = EditModulePage(self.driver, MODULE_ID)

        editModulePage.setCourseName(COURSE_NAME)
        editModulePage.setPointsToPass(POINTS_TO_PASS)
        editModulePage.setOpeningTime(OPENING_TIME)
        editModulePage.setClosingTime(CLOSING_TIME)
        editModulePage.submit()

        self.assertTrue(editModulePage.isSuccessfulSave())

        editModulePage = EditModulePage(self.driver, MODULE_ID)
        self.assertEqual(editModulePage.getCourseName(), COURSE_NAME)
        self.assertEqual(editModulePage.getPointsToPass(), POINTS_TO_PASS)
        self.assertEqual(editModulePage.getOpeningTime(), OPENING_TIME)
        self.assertEqual(editModulePage.getClosingTime(), CLOSING_TIME)

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
