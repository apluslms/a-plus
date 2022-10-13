from lib.testdata import CourseTestCase

from exercise.cache.content import CachedContent
from exercise.cache.points import CachedPoints
from .models import Threshold


class ThresholdTest(CourseTestCase):

    class MockCachedPoints:
        def __init__(self, total_data):
            self.data = total_data
        def total(self):
            return self.data

    GRADE_0 = MockCachedPoints({
        'points':8,
        'points_by_difficulty':{'A':1500,'B':200},
        'unconfirmed_points_by_difficulty':{'A':200,'B':200},
    })
    GRADE_1 = MockCachedPoints({
        'points':10,
        'points_by_difficulty':{'A':1800}
    })
    GRADE_2 = MockCachedPoints({
        'points':25,
        'points_by_difficulty':{'A':1900,'B':500}
    })
    GRADE_3 = MockCachedPoints({
        'points':39,
        'points_by_difficulty':{'A':1900,'B':875,'C':349}
    })
    GRADE_4 = MockCachedPoints({
        'points':48,
        'points_by_difficulty':{'A':1800,'B':775,'C':550}
    })
    GRADE_5 = MockCachedPoints({
        'points':100,
        'points_by_difficulty':{'A':1700,'B':0,'C':1775}
    })

    def setUp(self):
        self.setUpCourse()
        self.setUpSubmissions()
        self.grades = list([ # pylint: disable=consider-using-generator
            Threshold.objects.create(course_instance=self.instance, name=name)
            for name in ["1", "2", "3", "4", "5"]
        ])

    def _create_difficulty_thresholds(self):
        self.grades[0].points.create(limit=1800, difficulty="A", order=1)
        self.grades[0].points.create(limit=0, difficulty="B", order=2)
        self.grades[0].points.create(limit=0, difficulty="C", order=3)
        self.grades[1].points.create(limit=1900, difficulty="A", order=1)
        self.grades[1].points.create(limit=400, difficulty="B", order=2)
        self.grades[1].points.create(limit=0, difficulty="C", order=3)
        self.grades[2].points.create(limit=1900, difficulty="A", order=1)
        self.grades[2].points.create(limit=875, difficulty="B", order=2)
        self.grades[2].points.create(limit=0, difficulty="C", order=3)
        self.grades[3].points.create(limit=1900, difficulty="A", order=1)
        self.grades[3].points.create(limit=875, difficulty="B", order=2)
        self.grades[3].points.create(limit=350, difficulty="C", order=3)
        self.grades[4].points.create(limit=1900, difficulty="A", order=1)
        self.grades[4].points.create(limit=875, difficulty="B", order=2)
        self.grades[4].points.create(limit=600, difficulty="C", order=3)

    def test_normal_points(self):
        self.grades[0].points.create(limit=10)
        self.grades[1].points.create(limit=20)
        self.grades[2].points.create(limit=30)
        self.grades[3].points.create(limit=40)
        self.grades[4].points.create(limit=50)
        self.grades[3].consume_harder_points = True
        self.grades[3].save()
        self.assertFalse(self.grades[0].is_passed(self.GRADE_0))
        self.assertFalse(self.grades[4].is_passed(self.GRADE_0))
        self.assertTrue(self.grades[0].is_passed(self.GRADE_1))
        self.assertFalse(self.grades[1].is_passed(self.GRADE_1))
        self.assertTrue(self.grades[0].is_passed(self.GRADE_2))
        self.assertTrue(self.grades[1].is_passed(self.GRADE_2))
        self.assertFalse(self.grades[2].is_passed(self.GRADE_2))
        self.assertTrue(self.grades[2].is_passed(self.GRADE_3))
        self.assertFalse(self.grades[3].is_passed(self.GRADE_3))
        self.assertTrue(self.grades[3].is_passed(self.GRADE_4))
        self.assertFalse(self.grades[4].is_passed(self.GRADE_4))
        self.assertTrue(self.grades[4].is_passed(self.GRADE_5))
        self.assertTrue(self.grades[3].is_passed(self.GRADE_5))

    def test_difficulty_points(self):
        self._create_difficulty_thresholds()
        self.assertFalse(self.grades[0].is_passed(self.GRADE_0))
        self.assertFalse(self.grades[4].is_passed(self.GRADE_0))
        self.assertTrue(self.grades[0].is_passed(self.GRADE_1))
        self.assertFalse(self.grades[1].is_passed(self.GRADE_1))
        self.assertTrue(self.grades[0].is_passed(self.GRADE_2))
        self.assertTrue(self.grades[1].is_passed(self.GRADE_2))
        self.assertFalse(self.grades[2].is_passed(self.GRADE_2))
        self.assertTrue(self.grades[2].is_passed(self.GRADE_3))
        self.assertFalse(self.grades[3].is_passed(self.GRADE_3))
        self.assertTrue(self.grades[0].is_passed(self.GRADE_4))
        self.assertFalse(self.grades[1].is_passed(self.GRADE_4))
        self.assertFalse(self.grades[2].is_passed(self.GRADE_4))
        self.assertFalse(self.grades[3].is_passed(self.GRADE_4))
        self.assertFalse(self.grades[4].is_passed(self.GRADE_4))
        self.assertFalse(self.grades[0].is_passed(self.GRADE_5))
        self.assertFalse(self.grades[1].is_passed(self.GRADE_5))
        self.assertFalse(self.grades[2].is_passed(self.GRADE_5))
        self.assertFalse(self.grades[3].is_passed(self.GRADE_5))
        self.assertFalse(self.grades[4].is_passed(self.GRADE_5))

    def test_difficulty_points_consumed(self):
        self._create_difficulty_thresholds()
        for t in self.grades:
            t.consume_harder_points = True
            t.save()
        self.assertFalse(self.grades[0].is_passed(self.GRADE_0))
        self.assertFalse(self.grades[4].is_passed(self.GRADE_0))
        self.assertTrue(self.grades[0].is_passed(self.GRADE_1))
        self.assertFalse(self.grades[1].is_passed(self.GRADE_1))
        self.assertTrue(self.grades[0].is_passed(self.GRADE_2))
        self.assertTrue(self.grades[1].is_passed(self.GRADE_2))
        self.assertFalse(self.grades[2].is_passed(self.GRADE_2))
        self.assertTrue(self.grades[2].is_passed(self.GRADE_3))
        self.assertFalse(self.grades[3].is_passed(self.GRADE_3))
        self.assertTrue(self.grades[3].is_passed(self.GRADE_4))
        self.assertFalse(self.grades[4].is_passed(self.GRADE_4))
        self.assertTrue(self.grades[4].is_passed(self.GRADE_5))
        self.assertTrue(self.grades[3].is_passed(self.GRADE_5))
        self.assertTrue(self.grades[0].is_passed(self.GRADE_0, True))
        self.assertFalse(self.grades[1].is_passed(self.GRADE_0, True))

    def test_pass(self):
        content = CachedContent(self.instance)
        points = CachedPoints(self.instance, self.student, content)
        t = Threshold.objects.create(course_instance=self.instance, name="test")
        t.passed_categories.add(self.category)
        self.assertTrue(t.is_passed(points))
        t.passed_exercises.add(self.exercise)
        self.assertTrue(t.is_passed(points))
        t.passed_exercises.add(self.exercise2)
        self.assertFalse(t.is_passed(points))
        t.passed_exercises.clear()
        t.passed_modules.add(self.module)
        self.assertFalse(t.is_passed(points))
        self.submission3.set_points(2,2)
        self.submission3.set_ready()
        self.submission3.save()
        points = CachedPoints(self.instance, self.student, content)
        self.assertTrue(t.is_passed(points))
