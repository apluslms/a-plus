from course.models import CourseInstance
from exercise.models import BaseExercise
from lib.testdata import CourseTestCase


class CourseCloneTest(CourseTestCase):

    def test_course_clone(self):

        instance = CourseInstance.objects.get(id=1)
        instance.assistants.add(self.user.userprofile)
        instance_url = instance.url
        instance_str = str(instance)
        visible = instance.visible_to_students
        assistant_names = self._as_id(instance.assistants.all())
        module_names = self._as_names(instance.course_modules.all())

        url = instance.get_url('course-clone')
        self.client.login(username='testTeacher', password='testPassword')
        response = self.client.post(url, { 'url': 'another' }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "alert alert-danger")
        self.assertContains(response, "alert alert-success")

        instance = CourseInstance.objects.get(id=1)
        self.assertEqual(instance.url, instance_url)
        self.assertEqual(str(instance), instance_str)
        self.assertEqual(instance.visible_to_students, visible)
        self.assertEqual(self._as_id(instance.assistants.all()), assistant_names)
        self.assertEqual(self._as_names(instance.course_modules.all()), module_names)

        new_instance = CourseInstance.objects.get(course=instance.course, url="another")
        self.assertEqual(str(new_instance), instance_str)
        self.assertFalse(new_instance.visible_to_students)
        self.assertEqual(self._as_id(new_instance.assistants.all()), assistant_names)
        self.assertEqual(self._as_names(new_instance.course_modules.all()), module_names)

        old_modules = list(instance.course_modules.all())
        new_modules = list(new_instance.course_modules.all())
        self.assertEqual(len(old_modules), len(new_modules))
        for i in range(len(old_modules)):
            self.assertEqual(old_modules[i].url, new_modules[i].url)
            self.assertEqual(
                self._as_names(old_modules[i].learning_objects.all()),
                self._as_names(new_modules[i].learning_objects.all())
            )
            self.assertEqual(
                self._as_class(old_modules[i].learning_objects.all()),
                self._as_class(new_modules[i].learning_objects.all())
            )

        old_exercise = old_modules[1].learning_objects.first().as_leaf_class()
        new_exercise = new_modules[1].learning_objects.first().as_leaf_class()
        self.assertTrue(old_exercise.submissions.count() > 0)
        self.assertEqual(new_exercise.submissions.count(), 0)

    def _as_id(self, items):
        return [a.id for a in items]

    def _as_names(self, items):
        return [a.name for a in items]

    def _as_class(self, items):
        return [a.as_leaf_class().__class__ for a in items]


class BatchAssessTest(CourseTestCase):

    def setUp(self):
        self.setUpCourse()

    def test_batch_assess(self):
        from json import dumps

        instance = CourseInstance.objects.get(id=1)
        exercise = BaseExercise.objects.get(id=1)
        url = instance.get_url('batch-assess')

        json_to_post = dumps({
          'objects': [
            {
              'students_by_student_id': [self.student.userprofile.student_id],
              'feedback': 'Generic exercise feedback',
              'grader': self.teacher.userprofile.id,
              'exercise_id': 1,
              'submission_time': '2014-09-24 11:50',
              'points': 99
            }
          ]
        })

        self.client.login(username='testTeacher', password='testPassword')

        response = self.client.post('/course/instance/teachers/batch-assess/',
            {'submissions_json': json_to_post}, follow=True)

        self.assertContains(response, 'New submissions stored.')
        subs = exercise.get_submissions_for_student(self.student.userprofile, exclude_errors=True)
        self.assertEqual(len(subs), 1)
        sub = subs.first()
        self.assertEqual(sub.feedback, 'Generic exercise feedback')
        self.assertEqual(sub.grade, 99)
