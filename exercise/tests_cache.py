from lib.testdata import CourseTestCase
from course.models import CourseInstance, CourseModule, LearningObjectCategory
from deviations.models import MaxSubmissionsRuleDeviation
from exercise.tests import ExerciseTestBase
from .cache.content import CachedContent, InstanceContent, LearningObjectContent, ModuleContent
from .cache.hierarchy import previous_iterator
from .cache.points import (
    CachedPoints,
    CachedPointsData,
    LearningObjectPoints,
    ModulePoints,
    ExercisePoints,
)
from .models import BaseExercise, CourseChapter, LearningObject, RevealRule, StaticExercise, Submission
from deviations.models import DeadlineRuleDeviation


class CachedExerciseContentTest(ExerciseTestBase):
    def test_no_invalidation(self):
        base_entry = LearningObjectContent.get(self.base_exercise)
        base_entry2 = LearningObjectContent.get(self.base_exercise)
        self.assertEqual(base_entry._generated_on, base_entry2._generated_on)

    def test_invalidation_save(self):
        base_entry = LearningObjectContent.get(self.base_exercise)

        self.base_exercise.save()
        base_entry2 = LearningObjectContent.get(self.base_exercise)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)

        lobj_entry = LearningObjectContent.get(self.learning_object)
        lobj_entry2 = LearningObjectContent.get(self.learning_object)
        self.assertEqual(lobj_entry._generated_on, lobj_entry2._generated_on)

        self.base_exercise.parent = self.learning_object
        self.base_exercise.save()
        base_entry = LearningObjectContent.get(self.base_exercise)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        # learning_object children have changed
        lobj_entry2 = LearningObjectContent.get(self.learning_object)
        self.assertNotEqual(lobj_entry._generated_on, lobj_entry2._generated_on)

        self.base_exercise.parent = self.broken_learning_object
        self.base_exercise.save()
        # learning_object children have changed
        lobj_entry = LearningObjectContent.get(self.learning_object)
        self.assertNotEqual(lobj_entry._generated_on, lobj_entry2._generated_on)

        self.learning_object_category.save()
        base_entry2 = LearningObjectContent.get(self.base_exercise)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)

        self.course_module.save()
        base_entry = LearningObjectContent.get(self.base_exercise)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)

    def test_invalidation_delete_exercise(self):
        self.base_exercise.parent = self.learning_object
        self.base_exercise.save()
        # Create an entry in the cache
        LearningObjectContent.get(self.base_exercise)
        lobj_entry = LearningObjectContent.get(self.learning_object)
        self.base_exercise.delete()
        try:
            LearningObjectContent.get(self.base_exercise)
        except LearningObject.DoesNotExist:
            pass
        else:
            self.fail(
                "ExerciseEntry.get should have thrown a LearningObject.DoesNotExist"
                " exception for a non-existent exercise"
            )
        lobj_entry2 = LearningObjectContent.get(self.learning_object)
        self.assertNotEqual(lobj_entry._generated_on, lobj_entry2._generated_on)

    def test_invalidation_delete_module(self):
        base_entry = LearningObjectContent.get(self.base_exercise)
        self.course_module.delete()
        try:
            base_entry2 = LearningObjectContent.get(self.base_exercise)
        except LearningObject.DoesNotExist:
            pass
        else:
            self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)

    def test_invalidation_delete_category(self):
        base_entry = LearningObjectContent.get(self.base_exercise)
        self.learning_object_category.delete()
        try:
            base_entry2 = LearningObjectContent.get(self.base_exercise)
        except LearningObject.DoesNotExist:
            pass
        else:
            self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)


class CachedModuleContentTest(ExerciseTestBase):
    def test_no_invalidation(self):
        entry = ModuleContent.get(self.course_module)
        entry2 = ModuleContent.get(self.course_module)
        self.assertEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_save(self):
        entry = ModuleContent.get(self.course_module)

        self.course_module.save()
        entry2 = ModuleContent.get(self.course_module)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

        self.base_exercise.save()
        entry = ModuleContent.get(self.course_module)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

        self.learning_object_category.save()
        entry2 = ModuleContent.get(self.course_module)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_delete_module(self):
        # Create an entry in the cache
        ModuleContent.get(self.course_module)
        self.course_module.delete()
        try:
            ModuleContent.get(self.course_module)
        except CourseModule.DoesNotExist:
            pass
        else:
            self.fail(
                "ModuleEntry.get should have thrown a CourseModule.DoesNotExist exception for a non-existent module"
            )

    def test_invalidation_delete_exercise(self):
        entry = ModuleContent.get(self.course_module)

        self.base_exercise.delete()
        entry2 = ModuleContent.get(self.course_module)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_delete_category(self):
        entry = ModuleContent.get(self.course_module)

        self.learning_object_category.delete()
        entry2 = ModuleContent.get(self.course_module)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)


class CachedContentTest(CourseTestCase):
    def test_no_invalidation(self):
        entry = InstanceContent.get(self.instance)
        entry2 = InstanceContent.get(self.instance)
        self.assertEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation(self):
        entry = InstanceContent.get(self.instance)
        self.instance.save()
        entry2 = InstanceContent.get(self.instance)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

        self.module.save()
        entry = InstanceContent.get(self.instance)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

        self.exercise.save()
        entry2 = InstanceContent.get(self.instance)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

        self.category.save()
        entry = InstanceContent.get(self.instance)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_delete_instance(self):
        # Create an entry in the cache
        InstanceContent.get(self.instance)
        self.instance.delete()
        try:
            InstanceContent.get(self.instance)
        except CourseInstance.DoesNotExist:
            pass
        else:
            self.fail(
                "CachedContentData.get should have thrown a"
                " CourseInstance.DoesNotExist exception for a non-existent instance"
            )

    def test_invalidation_delete_module(self):
        entry = InstanceContent.get(self.instance)
        self.module.delete()
        entry2 = InstanceContent.get(self.instance)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_delete_exercise(self):
        entry = InstanceContent.get(self.instance)
        self.exercise.delete()
        entry2 = InstanceContent.get(self.instance)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_delete_category(self):
        entry = InstanceContent.get(self.instance)
        self.category.delete()
        entry2 = InstanceContent.get(self.instance)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_content(self):
        self.module0.status = CourseModule.STATUS.UNLISTED
        self.module0.save()
        c = CachedContent(self.instance)
        total = c.total()
        self.assertEqual(total.min_group_size, 1)
        self.assertEqual(total.max_group_size, 2)
        modules = c.modules()
        self.assertEqual(len(c.modules()), 3)
        self.assertEqual(len(c.categories()), 1)
        exercises0 = list(c.flat_module(modules[0], level_markers=False))
        exercises1 = list(c.flat_module(modules[1], level_markers=False))
        self.assertEqual(len(exercises0), 1)
        self.assertEqual(len(exercises1), 2)
        exercise = exercises0[0]
        self.assertEqual(exercise.module_id, modules[0].id)
        self.assertTrue(exercise.is_visible())
        self.assertFalse(exercise.is_listed())
        exercise = exercises1[0]
        self.assertEqual(exercise.module_id, modules[1].id)
        self.assertTrue(exercise.is_visible())
        self.assertTrue(exercise.is_visible())
        self.assertFalse(exercise.is_in_maintenance())
        self.assertEqual(exercise.opening_time, self.module.opening_time)
        self.assertEqual(exercise.closing_time, self.module.closing_time)
        self.assertEqual(exercise.points_to_pass, 0)
        self.assertEqual(exercise.max_points, 100)

    def test_hierarchy(self):
        c = CachedContent(self.instance)
        full = list(c.flat_full())
        hierarchy = [
            'level',
            'module','level','exercise','level',
            'module','level','exercise','exercise','level',
            'module','level','exercise','level',
            'level',
        ]
        for i,typ in enumerate(hierarchy):
            self.assertEqual(full[i].type, typ)

        full = list(c.flat_full(level_markers=False))
        hierarchy = [t for t in hierarchy if t != "level"]
        for i,typ in enumerate(hierarchy):
            self.assertEqual(full[i].type, typ)

        begin = c.begin()
        self.assertEqual(begin, full[1])

    def test_find(self):
        c = CachedContent(self.instance)
        module,tree,prev,nex = c.find(self.module)
        self.assertEqual(module.type, 'module')
        self.assertEqual(module.id, self.module.id)
        self.assertEqual(len(tree), 1)
        self.assertEqual(prev.type, 'exercise')
        self.assertEqual(prev.id, self.exercise0.id)
        self.assertEqual(nex.type, 'exercise')
        self.assertEqual(nex.id, self.exercise.id)
        eid = c.find_path(self.module.id, self.exercise2.get_path())
        self.assertEqual(eid, self.exercise2.id)
        exercise,tree,prev,nex = c.find(self.exercise2)
        self.assertEqual(exercise.type, 'exercise')
        self.assertEqual(exercise.id, self.exercise2.id)
        self.assertEqual(len(tree), 2)
        self.assertEqual(tree[0], module)
        self.assertEqual(prev.type, 'exercise')
        self.assertEqual(prev.id, self.exercise.id)
        self.assertEqual(nex.type, 'module')
        self.assertEqual(nex.id, self.module2.id)

    def test_backwards(self):
        c = CachedContent(self.instance)
        backwards = list(previous_iterator(c.modules()))
        hierarcy = [
            'exercise','module',
            'exercise','exercise','module',
            'exercise','module',
        ]
        for i,typ in enumerate(hierarcy):
            self.assertEqual(backwards[i].type, typ)

    def test_flat_modules(self):
        c = CachedContent(self.instance)
        sizes = [3,4,3]
        for i,m in enumerate(c.modules_flatted()):
            self.assertEqual(len(list(m.flatted)), sizes[i])

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
        _exercise, _tree, _prev, nex = c.find(self.subexercise)
        self.assertEqual(nex.type, 'module')
        self.assertEqual(nex.id, self.module2.id)


class CachedExercisePointsTest(ExerciseTestBase):
    def test_no_invalidation(self):
        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)
        base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertEqual(base_entry._generated_on, base_entry2._generated_on)

    def test_content_invalidated(self):
        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)
        LearningObjectContent.invalidate(self.base_exercise)
        base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)

    def test_invalidation_save(self):
        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)

        user2_base_entry = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.submission.submitters.add(self.user2.userprofile)
        base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        user2_base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.assertNotEqual(user2_base_entry._generated_on, user2_base_entry2._generated_on)

        self.submission.save()
        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        user2_base_entry = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.assertNotEqual(user2_base_entry._generated_on, user2_base_entry2._generated_on)

        self.deadline_rule_deviation.exercise = self.base_exercise
        self.deadline_rule_deviation.save()
        base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        user2_base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.assertNotEqual(user2_base_entry._generated_on, user2_base_entry2._generated_on)

        MaxSubmissionsRuleDeviation.objects.create(
            exercise=self.base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_submissions=1,
        )
        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        user2_base_entry = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.assertNotEqual(user2_base_entry._generated_on, user2_base_entry2._generated_on)

        reveal_rule = RevealRule.objects.create(
            trigger=RevealRule.TRIGGER.MANUAL,
        )
        self.base_exercise.submission_feedback_reveal_rule = reveal_rule
        self.base_exercise.save()
        base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)

        reveal_rule.save()
        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        user2_base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.assertNotEqual(user2_base_entry._generated_on, user2_base_entry2._generated_on)

    def test_invalidation_delete_submission(self):
        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)
        user2_base_entry = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.submission_with_two_submitters.delete()
        base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        user2_base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.assertNotEqual(user2_base_entry._generated_on, user2_base_entry2._generated_on)

    def test_invalidation_delete_reveal_rule(self):
        reveal_rule = RevealRule.objects.create(
            trigger=RevealRule.TRIGGER.MANUAL,
        )
        self.base_exercise.submission_feedback_reveal_rule = reveal_rule
        self.base_exercise.save()

        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)
        user2_base_entry = LearningObjectPoints.get(self.base_exercise, self.user2)
        reveal_rule.delete()
        base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        user2_base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.assertNotEqual(user2_base_entry._generated_on, user2_base_entry2._generated_on)

    def test_invalidation_delete_max_submission_rule_deviation(self):
        submission_rule_deviation = MaxSubmissionsRuleDeviation.objects.create(
            exercise=self.base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_submissions=1,
        )

        base_entry = LearningObjectPoints.get(self.base_exercise, self.user)
        user2_base_entry = LearningObjectPoints.get(self.base_exercise, self.user2)
        submission_rule_deviation.delete()
        base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user)
        self.assertNotEqual(base_entry._generated_on, base_entry2._generated_on)
        user2_base_entry2 = LearningObjectPoints.get(self.base_exercise, self.user2)
        self.assertNotEqual(user2_base_entry._generated_on, user2_base_entry2._generated_on)

    def test_invalidation_child_dependency(self):
        self.base_exercise.parent = self.learning_object
        lobj_entry = LearningObjectPoints.get(self.learning_object, self.user)
        self.base_exercise.save()
        lobj_entry2 = LearningObjectPoints.get(self.learning_object, self.user)
        self.assertNotEqual(lobj_entry._generated_on, lobj_entry2._generated_on)

        LearningObjectPoints.invalidate(self.base_exercise, self.user)
        lobj_entry = LearningObjectPoints.get(self.learning_object, self.user)
        self.assertNotEqual(lobj_entry._generated_on, lobj_entry2._generated_on)


class CachedModulePointsTest(ExerciseTestBase):
    def test_no_invalidation(self):
        entry = ModulePoints.get(self.course_module, self.user)
        entry2 = ModulePoints.get(self.course_module, self.user)
        self.assertEqual(entry._generated_on, entry2._generated_on)

    def test_content_invalidated(self):
        entry = ModulePoints.get(self.course_module, self.user)
        LearningObjectContent.invalidate(self.course_module)
        entry2 = ModulePoints.get(self.course_module, self.user)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_descendant_dependency(self):
        self.base_exercise.parent = self.learning_object
        self.base_exercise.save()

        entry = ModulePoints.get(self.course_module, self.user)
        self.base_exercise.save()
        entry2 = ModulePoints.get(self.course_module, self.user)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

        self.learning_object.save()
        entry = ModulePoints.get(self.course_module, self.user)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)


class CachedPointsTest(CourseTestCase):
    def test_no_invalidation(self):
        entry = CachedPointsData.get(self.instance, self.user)
        entry2 = CachedPointsData.get(self.instance, self.user)
        self.assertEqual(entry._generated_on, entry2._generated_on)

    def test_content_invalidated(self):
        entry = CachedPointsData.get(self.instance, self.user)
        InstanceContent.invalidate(self.instance)
        entry2 = CachedPointsData.get(self.instance, self.user)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_module_dependency(self):
        entry = CachedPointsData.get(self.instance, self.user)
        self.module.save()
        entry2 = CachedPointsData.get(self.instance, self.user)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

        ModulePoints.invalidate(self.module, self.user)
        entry = CachedPointsData.get(self.instance, self.user)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation_exercise_dependency(self):
        entry = CachedPointsData.get(self.instance, self.user)
        self.exercise.save()
        entry2 = CachedPointsData.get(self.instance, self.user)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

        LearningObjectPoints.invalidate(self.module, self.user)
        entry = CachedPointsData.get(self.instance, self.user)
        self.assertNotEqual(entry._generated_on, entry2._generated_on)

    def test_invalidation(self):
        p = CachedPoints(self.instance, self.student)
        created = p.created()
        p = CachedPoints(self.instance, self.student)
        self.assertEqual(p.created(), created)
        self.exercise0.save()
        p = CachedPoints(self.instance, self.student)
        self.assertNotEqual(p.created(), created)
        created = p.created()
        self.submission2.save()
        c = CachedContent(self.instance)
        p = CachedPoints(self.instance, self.student)
        self.assertEqual(c.created(), created[1])
        self.assertNotEqual(p.created(), created)

    def test_accumulation(self):
        self.submission2.set_points(2,2)
        self.submission2.save()
        p = CachedPoints(self.instance, self.student)
        entry, _tree, _, _ = p.find(self.exercise)
        self.assertTrue(entry.graded)
        self.assertTrue(entry.passed)
        self.assertEqual(entry.points, 50)
        total = p.total()
        self.assertEqual(total.submission_count, 2)
        self.assertEqual(total.points, 50)
        self.assertEqual(total.points_by_difficulty.get('',0), 50)
        module = p.modules()[1]
        self.assertEqual(module.submission_count, 2)
        self.assertEqual(module.points, 50)
        self.assertEqual(module.points_by_difficulty.get('',0), 50)
        self.assertFalse(module.passed)
        category = p.categories()[0]
        self.assertTrue(category.passed)

        self.submission2.set_ready()
        self.submission2.save()
        p = CachedPoints(self.instance, self.student)
        total = p.total()
        self.assertEqual(total.submission_count, 2)
        self.assertEqual(total.points, 100)
        self.assertEqual(total.points_by_difficulty.get('',0), 100)

        self.submission3.set_points(10,100)
        self.submission3.set_ready()
        self.submission3.save()
        p = CachedPoints(self.instance, self.student)
        total = p.total()
        self.assertEqual(total.submission_count, 3)
        self.assertEqual(total.points, 110)
        self.assertEqual(total.points_by_difficulty.get('',0), 110)
        module = p.modules()[1]
        self.assertTrue(module.passed)

    def test_unconfirmed(self):
        self.category2 = LearningObjectCategory.objects.create(
            course_instance=self.instance,
            name="Test Category 2",
            points_to_pass=5,
            confirm_the_level=True,
        )
        self.exercise2.category = self.category2
        self.exercise2.save()
        p = CachedPoints(self.instance, self.student)
        total = p.total()
        self.assertEqual(total.points, 0)
        self.assertEqual(total.points_by_difficulty.get('',0), 0)
        self.assertEqual(total.unconfirmed_points_by_difficulty.get('',0), 50)
        module = p.modules()[1]
        self.assertEqual(module.points, 0)
        category = p.categories()[0]
        self.assertEqual(category.points, 0)

        self.submission3.set_points(1,2)
        self.submission3.set_ready()
        self.submission3.save()
        p = CachedPoints(self.instance, self.student)
        total = p.total()
        self.assertEqual(total.points, 50)
        self.assertEqual(total.points_by_difficulty.get('',0), 50)
        self.assertEqual(total.unconfirmed_points_by_difficulty.get('',0), 0)
        module = p.modules()[1]
        self.assertEqual(module.points, 50)
        category = p.categories()[0]
        self.assertEqual(category.points, 50)

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

        p = CachedPoints(self.instance, self.student)
        entry,_,_,_ = p.find(self.exercise3)
        self.assertFalse(entry.graded)
        self.assertTrue(entry.unofficial)
        self.assertEqual(entry.points, 50)
        entry,_,_,_ = p.find(self.exercise)
        self.assertTrue(entry.graded)
        self.assertFalse(entry.unofficial)
        self.assertEqual(entry.points, 50)

    def test_is_revealed(self):
        module_chapter = CourseChapter.objects.create(
            name="test course chapter",
            course_module=self.module,
            category=self.category,
            url="c1",
        )
        DeadlineRuleDeviation.objects.create(
            exercise=self.exercise0,
            submitter=self.student.userprofile,
            granter=self.teacher.userprofile,
            extra_minutes=2*24*60,
        )
        reveal_rule = RevealRule.objects.create(
            trigger=RevealRule.TRIGGER.DEADLINE,
        )
        self.exercise.parent = module_chapter
        self.exercise.save()
        self.module0.model_answer = module_chapter
        self.module0.model_solution_reveal_rule = reveal_rule
        self.module0.save()
        p = CachedPoints(self.instance, self.student)
        entry0, _, _, _ = p.find(self.exercise0)
        entry, _, _, _ = p.find(self.exercise)
        entry2, _, _, _ = p.find(self.exercise2)
        chapter_entry, _, _, _ = p.find(module_chapter)
        self.assertTrue(entry0.is_revealed)
        self.assertFalse(entry.is_revealed)
        self.assertTrue(entry2.is_revealed)
        self.assertFalse(chapter_entry.is_revealed)

class ExercisePointsTest(ExerciseTestBase):
    def test_forced_points(self) -> None:
        self.submission.set_points(5, 10)
        self.submission.status = Submission.STATUS.READY
        self.submission.save()
        entry = ExercisePoints.get(self.base_exercise, self.user)
        self.assertEqual(entry.official_points, 50)
        self.assertEqual(entry.points, 50)

        forced_points_submission = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.userprofile,
        )
        forced_points_submission.submitters.add(self.user.userprofile)
        forced_points_submission.set_points(1, 10)
        forced_points_submission.save()
        entry = ExercisePoints.get(self.base_exercise, self.user)
        self.assertEqual(entry.official_points, 50)
        self.assertEqual(entry.points, 50)

        self.submission.status = Submission.STATUS.UNOFFICIAL
        self.submission.save()
        entry = ExercisePoints.get(self.base_exercise, self.user)
        self.assertEqual(entry.official_points, 0)
        self.assertEqual(entry.points, 50)

        self.submission.status = Submission.STATUS.READY
        self.submission.save()
        forced_points_submission.force_exercise_points = True
        forced_points_submission.save()
        entry = ExercisePoints.get(self.base_exercise, self.user)
        self.assertEqual(entry.official_points, 10)
        self.assertEqual(entry.points, 10)

        forced_points_submission.status = Submission.STATUS.READY
        forced_points_submission.force_exercise_points = False
        forced_points_submission.save()
        self.submission.status = Submission.STATUS.UNOFFICIAL
        self.submission.save()
        entry = ExercisePoints.get(self.base_exercise, self.user)
        self.assertEqual(entry.official_points, 10)
        self.assertEqual(entry.points, 10)

        forced_points_submission.delete()
        entry = ExercisePoints.get(self.base_exercise, self.user)
        self.assertEqual(entry.official_points, 0)
        self.assertEqual(entry.points, 50)

        self.submission.status = Submission.STATUS.READY
        self.submission.save()
        entry = ExercisePoints.get(self.base_exercise, self.user)
        self.assertEqual(entry.official_points, 50)
        self.assertEqual(entry.points, 50)
