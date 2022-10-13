from lib.testdata import CourseTestCase
from course.models import CourseModule, LearningObjectCategory
from .cache.content import CachedContent
from .cache.hierarchy import PreviousIterator
from .cache.points import CachedPoints
from .models import BaseExercise, StaticExercise, Submission


class CachedContentTest(CourseTestCase):

    def test_invalidation(self):
        c = CachedContent(self.instance)
        created = c.created()
        c = CachedContent(self.instance)
        self.assertEqual(c.created(), created)
        self.exercise0.save()
        c = CachedContent(self.instance)
        self.assertNotEqual(c.created(), created)

    def test_content(self):
        self.module0.status = CourseModule.STATUS.UNLISTED
        self.module0.save()
        c = CachedContent(self.instance)
        self.assertFalse(c.dirty)
        total = c.total()
        self.assertEqual(total['min_group_size'], 1)
        self.assertEqual(total['max_group_size'], 2)
        modules = c.modules()
        self.assertEqual(len(c.modules()), 3)
        self.assertEqual(len(c.categories()), 1)
        exercises0 = list(c.flat_module(modules[0], enclosed=False))
        exercises1 = list(c.flat_module(modules[1], enclosed=False))
        self.assertEqual(len(exercises0), 1)
        self.assertEqual(len(exercises1), 2)
        exercise = exercises0[0]
        self.assertEqual(exercise['module_id'], modules[0]['id'])
        self.assertTrue(CachedContent.is_visible(exercise))
        self.assertFalse(CachedContent.is_listed(exercise))
        exercise = exercises1[0]
        self.assertEqual(exercise['module_id'], modules[1]['id'])
        self.assertTrue(CachedContent.is_visible(exercise))
        self.assertTrue(CachedContent.is_listed(exercise))
        self.assertFalse(CachedContent.is_in_maintenance(exercise))
        self.assertEqual(exercise['opening_time'], self.module.opening_time)
        self.assertEqual(exercise['closing_time'], self.module.closing_time)
        self.assertEqual(exercise['points_to_pass'], 0)
        self.assertEqual(exercise['max_points'], 100)

    def test_hierarchy(self):
        c = CachedContent(self.instance)
        full = list(c.flat_full())
        hierarchy = [
            'module','level','exercise','level',
            'module','level','exercise','exercise','level',
            'module','level','exercise','level',
        ]
        for i,typ in enumerate(hierarchy):
            self.assertEqual(full[i]['type'], typ)
        begin = c.begin()
        self.assertEqual(begin, full[2])

    def test_find(self):
        c = CachedContent(self.instance)
        module,tree,prev,nex = c.find(self.module)
        self.assertEqual(module['type'], 'module')
        self.assertEqual(module['id'], self.module.id)
        self.assertEqual(len(tree), 1)
        self.assertEqual(prev['type'], 'exercise')
        self.assertEqual(prev['id'], self.exercise0.id)
        self.assertEqual(nex['type'], 'exercise')
        self.assertEqual(nex['id'], self.exercise.id)
        eid = c.find_path(self.module.id, self.exercise2.get_path())
        self.assertEqual(eid, self.exercise2.id)
        exercise,tree,prev,nex = c.find(self.exercise2)
        self.assertEqual(exercise['type'], 'exercise')
        self.assertEqual(exercise['id'], self.exercise2.id)
        self.assertEqual(len(tree), 2)
        self.assertEqual(tree[0], module)
        self.assertEqual(prev['type'], 'exercise')
        self.assertEqual(prev['id'], self.exercise.id)
        self.assertEqual(nex['type'], 'module')
        self.assertEqual(nex['id'], self.module2.id)

    def test_backwards(self):
        c = CachedContent(self.instance)
        backwards = list(PreviousIterator(c.modules()))
        hierarcy = [
            'exercise','module',
            'exercise','exercise','module',
            'exercise','module',
        ]
        for i,typ in enumerate(hierarcy):
            self.assertEqual(backwards[i]['type'], typ)

    def test_flat_modules(self):
        c = CachedContent(self.instance)
        sizes = [3,4,3]
        for i,m in enumerate(c.modules_flatted()):
            self.assertEqual(len(list(m['flatted'])), sizes[i])

    def test_deep(self):
        self.subexercise = StaticExercise.objects.create(
            course_module=self.module,
            category=self.category,
            parent=self.exercise2,
            status=BaseExercise.STATUS.UNLISTED,
            url='s1',
            name="Deep Exercise",
            exercise_page_content='$$subexercise$$content',
            submission_page_content='$$subexercise$$received',
            points_to_pass=0,
            max_points=100,
            order=1,
        )
        c = CachedContent(self.instance)
        _exercise,_tree,_prev,nex = c.find(self.subexercise)
        self.assertEqual(nex['type'], 'module')
        self.assertEqual(nex['id'], self.module2.id)


class CachedPointsTest(CourseTestCase):

    def test_invalidation(self):
        c = CachedContent(self.instance)
        p = CachedPoints(self.instance, self.student, c)
        self.assertFalse(p.dirty)
        created = p.created()
        c = CachedContent(self.instance)
        p = CachedPoints(self.instance, self.student, c)
        self.assertEqual(p.created(), created)
        self.exercise0.save()
        c = CachedContent(self.instance)
        p = CachedPoints(self.instance, self.student, c)
        self.assertNotEqual(p.created(), created)
        created = p.created()
        self.submission2.save()
        c = CachedContent(self.instance)
        p = CachedPoints(self.instance, self.student, c)
        self.assertEqual(c.created(), created[1])
        self.assertNotEqual(p.created(), created)

    def test_accumulation(self):
        self.submission2.set_points(2,2)
        self.submission2.save()
        c = CachedContent(self.instance)
        p = CachedPoints(self.instance, self.student, c)
        entry,_tree,_,_ = p.find(self.exercise)
        self.assertTrue(entry['graded'])
        self.assertTrue(entry['passed'])
        self.assertEqual(entry['points'], 50)
        total = p.total()
        self.assertEqual(total['submission_count'], 2)
        self.assertEqual(total['points'], 50)
        self.assertEqual(total['points_by_difficulty'].get('',0), 50)
        module = p.modules()[1]
        self.assertEqual(module['submission_count'], 2)
        self.assertEqual(module['points'], 50)
        self.assertEqual(module['points_by_difficulty'].get('',0), 50)
        self.assertFalse(module['passed'])
        category = p.categories()[0]
        self.assertTrue(category['passed'])

        self.submission2.set_ready()
        self.submission2.save()
        p = CachedPoints(self.instance, self.student, c)
        total = p.total()
        self.assertEqual(total['submission_count'], 2)
        self.assertEqual(total['points'], 100)
        self.assertEqual(total['points_by_difficulty'].get('',0), 100)

        self.submission3.set_points(10,100)
        self.submission3.set_ready()
        self.submission3.save()
        p = CachedPoints(self.instance, self.student, c)
        total = p.total()
        self.assertEqual(total['submission_count'], 3)
        self.assertEqual(total['points'], 110)
        self.assertEqual(total['points_by_difficulty'].get('',0), 110)
        module = p.modules()[1]
        self.assertTrue(module['passed'])

    def test_unconfirmed(self):
        self.category2 = LearningObjectCategory.objects.create(
            course_instance=self.instance,
            name="Test Category 2",
            points_to_pass=5,
            confirm_the_level=True,
        )
        self.exercise2.category = self.category2
        self.exercise2.save()
        c = CachedContent(self.instance)
        p = CachedPoints(self.instance, self.student, c)
        total = p.total()
        self.assertEqual(total['points'], 0)
        self.assertEqual(total['points_by_difficulty'].get('',0), 0)
        self.assertEqual(total['unconfirmed_points_by_difficulty'].get('',0), 50)
        module = p.modules()[1]
        self.assertEqual(module['points'], 0)
        category = p.categories()[0]
        self.assertEqual(category['points'], 0)

        self.submission3.set_points(1,2)
        self.submission3.set_ready()
        self.submission3.save()
        p = CachedPoints(self.instance, self.student, c)
        total = p.total()
        self.assertEqual(total['points'], 50)
        self.assertEqual(total['points_by_difficulty'].get('',0), 50)
        self.assertEqual(total['unconfirmed_points_by_difficulty'].get('',0), 0)
        module = p.modules()[1]
        self.assertEqual(module['points'], 50)
        category = p.categories()[0]
        self.assertEqual(category['points'], 50)

    def test_unofficial(self):
        self.module.late_submissions_allowed = False
        self.module.save()
        self.category.accept_unofficial_submits = True
        self.category.save()

        sub = Submission.objects.create(exercise=self.exercise3)
        sub.submitters.add(self.student.userprofile)
        sub.submission_time = self.three_days_after
        sub.set_points(1,2)
        sub.set_ready()
        sub.save()

        self.submission2.submission_time = self.three_days_after
        self.submission2.set_points(2,2)
        self.submission2.set_ready()
        self.submission2.save()

        c = CachedContent(self.instance)
        p = CachedPoints(self.instance, self.student, c)
        entry,_,_,_ = p.find(self.exercise3)
        self.assertFalse(entry['graded'])
        self.assertTrue(entry['unofficial'])
        self.assertEqual(entry['points'], 50)
        entry,_,_,_ = p.find(self.exercise)
        self.assertTrue(entry['graded'])
        self.assertFalse(entry['unofficial'])
        self.assertEqual(entry['points'], 50)
