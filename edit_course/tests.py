from datetime import datetime, timedelta
from json import dumps
from django.test import override_settings
from django.utils.translation import override as translation_override
from course.models import CourseInstance
from exercise.models import BaseExercise
from edit_course.course_forms import CourseModuleForm
from lib.testdata import CourseTestCase


class CourseModuleEditTest(CourseTestCase):

    def test_early_bonus_taper_tooltip_reflects_configuration(self):
        self.module.early_submission_deadline = self.now
        self.module.closing_time = self.now + timedelta(hours=29)
        self.module.early_submission_bonus = 0.15
        self.module.bonus_time_step_hours = 8

        with translation_override('en'):
            form = CourseModuleForm(instance=self.module)

        step_field = form.fields['bonus_time_step_hours']
        self.assertEqual(step_field.widget.attrs['data-bs-toggle'], 'tooltip')
        self.assertIn('3 steps, each lasting 8 hours', step_field.widget.attrs['title'])
        self.assertIn('decreases by 5 percentage points', step_field.widget.attrs['title'])
        self.assertIn('remaining time before the module deadline has no bonus', step_field.widget.attrs['title'])

    def test_edit_page_includes_early_submission_deadline(self):
        self.client.login(username='testTeacher', password='testPassword')
        url = self.instance.get_url(
            'model-edit',
            model='module',
            id=self.module.id,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        for field_name in (
            'early_submission_deadline',
            'early_submission_bonus_in_use',
            'early_submission_bonus',
            'bonus_time_step_hours',
        ):
            self.assertContains(response, f'name="{field_name}"')
        self.assertEqual(
            response.context['form'].fields['early_submission_bonus_in_use'].widget.input_type,
            'checkbox',
        )
        schedule_fields = response.context['form'].get_fieldsets()[-1]['fields']
        self.assertEqual(
            [field.name for field in schedule_fields],
            [
                'reading_opening_time',
                'opening_time',
                'closing_time',
                'late_submissions_allowed',
                'late_submission_deadline',
                'late_submission_penalty',
                'early_submission_bonus_in_use',
                'early_submission_deadline',
                'early_submission_bonus',
                'bonus_time_step_hours',
            ],
        )


class CourseCloneTest(CourseTestCase):

    def test_course_clone(self):

        instance = CourseInstance.objects.get(id=1)
        instance.add_assistant(self.user.userprofile)
        instance_url = instance.url
        course_name = instance.course.name
        visible = instance.visible_to_students
        teacher_names = self._as_id(instance.teachers.all())
        assistant_names = self._as_id(instance.assistants.all())

        url = instance.get_url('course-clone')
        self.client.login(username='testTeacher', password='testPassword')

        # Full clone
        response = self.client.post(url, {
            'url': 'another1',
            'instance_name': 'instance1',
            'teachers': True,
            'assistants': True,
            'menuitems': True,
            'usertags': True,
            'key_year': 2022,
            'key_month': 'Test',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        stripped_content = response.content.decode("utf-8").replace("modal-submit-error alert alert-danger", "")
        self.assertNotIn("alert alert-danger", stripped_content)
        self.assertIn("alert alert-success", stripped_content)

        # Partial clone
        response = self.client.post(url, {
            'url': 'another2',
            'instance_name': 'instance2',
            'teachers': True,
            'assistants': False,
            'menuitems': False,
            'usertags': False,
            'key_year': 2022,
            'key_month': 'Test',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        stripped_content = response.content.decode("utf-8").replace("modal-submit-error alert alert-danger", "")
        self.assertNotIn("alert alert-danger", stripped_content)
        self.assertIn("alert alert-success", stripped_content)

        instance = CourseInstance.objects.get(id=1)
        self.assertEqual(instance.url, instance_url)
        self.assertEqual(instance.course.name, course_name)
        self.assertEqual(instance.visible_to_students, visible)
        self.assertEqual(self._as_id(instance.teachers.all()), teacher_names)
        self.assertEqual(self._as_id(instance.assistants.all()), assistant_names)

        # Check the full clone
        new_instance_1 = CourseInstance.objects.get(course=instance.course, url="another1")
        self.assertEqual(new_instance_1.course.name, course_name)
        self.assertEqual(new_instance_1.instance_name, "instance1")
        self.assertFalse(new_instance_1.visible_to_students)
        self.assertEqual(self._as_id(new_instance_1.teachers.all()), teacher_names)
        self.assertEqual(self._as_id(new_instance_1.assistants.all()), assistant_names)

        # Check the partial clone
        new_instance_2 = CourseInstance.objects.get(course=instance.course, url="another2")
        self.assertEqual(new_instance_2.course.name, course_name)
        self.assertEqual(new_instance_2.instance_name, "instance2")
        self.assertFalse(new_instance_2.visible_to_students)
        self.assertEqual(self._as_id(new_instance_2.teachers.all()), teacher_names)
        self.assertEqual(new_instance_2.assistants.count(), 0)

    def _as_id(self, items):
        return [a.id for a in items]

    def _as_names(self, items):
        return [a.name for a in items]

    def _as_class(self, items):
        return [a.__class__ for a in items]

    @override_settings(SIS_PLUGIN_MODULE = 'course.sis_test')
    @override_settings(SIS_PLUGIN_CLASS = 'SisTest')
    def test_clone_from_sis(self):
        instance = CourseInstance.objects.get(id=1)

        url = instance.get_url('course-clone')
        self.client.login(username='testTeacher', password='testPassword')

        # Full clone
        response = self.client.post(url, {
            'url': 'sis-test',
            'instance_name': 'sis-instance',
            'teachers': True,
            'assistants': True,
            'menuitems': True,
            'usertags': True,
            'key_year': 2022,
            'key_month': 'Test',
            'sis': '123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        stripped_content = response.content.decode("utf-8").replace("modal-submit-error alert alert-danger", "")
        self.assertNotIn("alert alert-danger", stripped_content)
        self.assertIn("alert alert-success", stripped_content)

        # The asserted values are coming from in sis_test.py
        sis_instance = CourseInstance.objects.get(course=instance.course, url="sis-test")
        self.assertFalse(sis_instance.visible_to_students)
        self.assertEqual(
            list(a.user.username for a in sis_instance.teachers.all()),
            [ "testTeacher", "teacher-A" ]
        )
        self.assertEqual(
            sis_instance.starting_time,
            datetime.fromisoformat("2022-05-31 21:00:00+00:00")
        )
        self.assertEqual(
            sis_instance.ending_time,
            datetime.fromisoformat("2022-08-19 21:00:00+00:00")
        )

class BatchAssessTest(CourseTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.setUpCourse()

    def test_batch_assess(self):

        instance = CourseInstance.objects.get(id=1)
        exercise = BaseExercise.objects.get(id=1)
        url = instance.get_url('batch-assess') # pylint: disable=unused-variable

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
