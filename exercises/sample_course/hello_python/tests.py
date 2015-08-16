import unittest, pointstest

class TestHelloPython(pointstest.PointsTestCase):
    ACHIEVEMENTS = {
        "import": 1,
        "function": 1,
        "return": 3,
    }

    def test_import(self):
        """Import the functions module: 1p"""
        import functions
        self._pass("import")

    def test_function(self):
        """Check hello function exists: 1p"""
        import functions
        def protofunction():
            pass
        self.assertTrue(type(functions.hello), type(protofunction))
        self._pass("function")

    def test_return(self):
        """Check hello function return value: 3p"""
        import functions
        self.assertEqual(functions.hello(), "Hello Python!")
        self._pass("return")

if __name__ == '__main__':
    unittest.main(verbosity=2)
