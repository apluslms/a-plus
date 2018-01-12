import unittest

from test_initializer import TestInitializer
from page_objects import LoginPage, EditExercisePage, CourseName


class EditExercisePageTest(unittest.TestCase):
    def setUp(self):
        self.driver = TestInitializer().getDefaultDriver()
        TestInitializer().recreateDatabase()
        LoginPage(self.driver).loginAsTeacher()

    def testShouldSaveExercise(self):
        exerciseName = "Testiharjoitus"
        maxSubmissions = "5"
        maxPoints = "99"
        pointToPass = "50"
        exerciseNumber = 1

        editExercisePage = EditExercisePage(self.driver, exerciseNumber)

        editExercisePage.setExerciseName(exerciseName)
        editExercisePage.setMaxSubmissions(maxSubmissions)
        editExercisePage.setMaxPoints(maxPoints)
        editExercisePage.setPointsToPass(pointToPass)
        editExercisePage.submit()

        self.assertTrue(editExercisePage.isSuccessfulSave())

        editExercisePage = EditExercisePage(self.driver, exerciseNumber)
        self.assertEqual(editExercisePage.getExerciseName(), exerciseName)
        self.assertEqual(editExercisePage.getMaxSubmissions(), maxSubmissions)
        self.assertEqual(editExercisePage.getMaxPoints(), maxPoints)
        self.assertEqual(editExercisePage.getPointsToPass(), pointToPass)

    def tearDown(self):
        self.driver.quit()

if __name__ == '__main__':
    unittest.main(verbosity=2)
