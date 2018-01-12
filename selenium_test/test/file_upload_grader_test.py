import unittest

from test_initializer import TestInitializer
from page_objects import CourseName, LoginPage, FileUploadGrader


class FileUploadGraderTest(unittest.TestCase):
    def setUp(self):
        testInitializer = TestInitializer()
        self.driver = testInitializer.getDefaultDriver()
        testInitializer.recreateDatabase()
        LoginPage(self.driver).loginAsStudent()

    def testShouldGiveZeroPointsOnEmptySubmit(self):
        fileUploadPage = FileUploadGrader(self.driver)
        fileUploadPage.submit()

        # Submit without files will be in error state and not counted.
        self.assertEqual(fileUploadPage.getAllowedSubmissions(), '0 / 10')

        self.assertEqual(fileUploadPage.getExerciseScore(), '0 / 100')
        self.assertEqual(fileUploadPage.getNumberOfSubmitters(), '1')
        #self.assertEqual(fileUploadPage.getAverageSubmissionsPerStudent(), '1.00')

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
