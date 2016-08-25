from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from course.models import Course, CourseInstance, CourseModule, LearningObjectCategory
from exercise.submission_models import Submission
from exercise.exercise_models import BaseExercise, ExerciseWithAttachment
from exercise.submission_models import Submission


class InitialDataTests(TestCase):

    def setUp(self):
        now = timezone.now()

        self.user = User(username='testUser')
        self.user.set_password('testPassword')
        self.user.save()

        self.teacher = User(username='testTeacher')
        self.teacher.set_password('testPassword')
        self.teacher.save()

        self.student = User(username='testStudent')
        self.student.set_password('testPassword')
        self.student.save()
        self.student.userprofile.student_id = "123TEST"
        self.student.userprofile.save()

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="course",
        )
        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=now,
            ending_time=now + timedelta(days=1),
            course=self.course,
            url="instance",
        )
        self.course_module = CourseModule.objects.create(
            name="test module",
            url="module",
            points_to_pass=10,
            course_instance=self.course_instance,
            opening_time=now,
            closing_time=now + timedelta(days=1),
        )
        self.course_module2 = CourseModule.objects.create(
            name="test module 2",
            url="module2",
            points_to_pass=10,
            course_instance=self.course_instance,
            opening_time=now + timedelta(days=1),
            closing_time=now + timedelta(days=2),
        )
        self.learning_object_category = LearningObjectCategory.objects.create(
            name="test category",
            course_instance=self.course_instance,
            points_to_pass=5,
        )
        self.base_exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.course_module,
            category=self.learning_object_category,
            service_url="http://localhost/",
            url='b1',
        )
        self.base_exercise2 = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.course_module,
            category=self.learning_object_category,
            service_url="http://localhost/",
            url='b2',
        )
        self.base_exercise3 = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.course_module2,
            category=self.learning_object_category,
            service_url="http://localhost/",
            url='b3',
        )


class CourseCloneTests(InitialDataTests):

    def test_course_clone(self):

        instance = CourseInstance.objects.get(id=1)
        instance.course.teachers.add(self.user.userprofile)
        instance_url = instance.url
        instance_str = str(instance)
        visible = instance.visible_to_students
        assistant_names = self._as_names(instance.assistants.all())
        module_names = self._as_names(instance.course_modules.all())

        url = instance.get_url('course-clone')
        self.client.login(username='testUser', password='testPassword')
        response = self.client.post(url, { 'url': 'another' }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "alert alert-danger")
        self.assertContains(response, "alert alert-success")

        instance = CourseInstance.objects.get(id=1)
        self.assertEqual(instance.url, instance_url)
        self.assertEqual(str(instance), instance_str)
        self.assertEqual(instance.visible_to_students, visible)
        self.assertEqual(self._as_names(instance.assistants.all()), assistant_names)
        self.assertEqual(self._as_names(instance.course_modules.all()), module_names)

        new_instance = CourseInstance.objects.get(course=instance.course, url="another")
        self.assertEqual(str(new_instance), instance_str)
        self.assertFalse(new_instance.visible_to_students)
        self.assertEqual(self._as_names(new_instance.assistants.all()), assistant_names)
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

    def test_clone_submissions(self):
        instance = CourseInstance.objects.get(id=1)
        module = instance.course_modules.first()
        n = module.learning_objects.count()
        exercise = ExerciseWithAttachment(
            category=instance.categories.first(),
            course_module=instance.course_modules.first(),
            url="",
            name="Clone Test",
        )
        exercise.save()
        self.assertEqual(module.learning_objects.count(), n + 1)
        submission = Submission(exercise=exercise)
        submission.save()
        submission.submitters.add(self.user.userprofile)
        self.assertEqual(exercise.submissions.count(), 1)

        from .operations.clone import clone
        new_instance = clone(instance, 'cloned')
        new_module = new_instance.course_modules.first()
        self.assertEqual(instance.course_modules.count(), new_instance.course_modules.count())
        self.assertEqual(module.learning_objects.count(), n + 1)
        self.assertEqual(new_module.learning_objects.count(), n + 1)
        self.assertEqual(ExerciseWithAttachment.objects.filter(course_module=module).count(), 1)
        self.assertEqual(ExerciseWithAttachment.objects.filter(course_module=new_module).count(), 1)
        new_exercise = ExerciseWithAttachment.objects.filter(course_module=new_module).first()
        self.assertEqual(exercise.submissions.count(), 1)
        self.assertEqual(new_exercise.submissions.count(), 0)

    def _as_names(self, items):
        return [a.name for a in items]

    def _as_class(self, items):
        return [a.as_leaf_class().__class__ for a in items]


class BatchAssessTest(InitialDataTests):

    def test_batch_assess(self):
        from json import dumps

        instance = CourseInstance.objects.get(id=1)
        instance.course.teachers.add(self.teacher.userprofile)
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

        #response = self.client.post('/aplus1/basic_instance/teachers/batch-assess/',
        #    {'submissions_json': json_to_post}, follow=True)

        response = self.client.post('/course/instance/teachers/batch-assess/',
            {'submissions_json': json_to_post}, follow=True)

        self.assertContains(response, 'New submissions stored.')
        subs = exercise.get_submissions_for_student(self.student.userprofile, exclude_errors=True)
        self.assertEqual(len(subs), 1)
        sub = subs.first()
        self.assertEqual(sub.feedback, 'Generic exercise feedback')
        self.assertEqual(sub.grade, 99)
