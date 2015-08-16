import unittest

class PointsTestCase(unittest.TestCase):
    """
    One way to keep point count over all tests in a test case.
    Finally prints out the result lines for the mooc-grader.
    """
    _passed_keys = []
    ACHIEVEMENTS = {
        #"a key": 10,
    }

    def _pass(self, key):
        """ Marks a certain achievement passed. """
        self.__class__._passed_keys.append(key)

    @classmethod
    def tearDownClass(cls):
        points = 0
        max_points = 0
        for key, reward in cls.ACHIEVEMENTS.items():
            max_points += reward
            if key in cls._passed_keys:
                points += reward
        print("TotalPoints: {:d}\n".format(points))
        print("MaxPoints: {:d}\n".format(max_points))
