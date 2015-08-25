from django.contrib.auth.models import User
from django.test import TestCase

from course.models import CourseInstance


class EditCourseTests(TestCase):
    fixtures = [ 'doc/initial_data.json' ]

    def setUp(self):
        self.user = User(username='testUser')
        self.user.set_password('testPassword')
        self.user.save()

    def test_course_clone(self):

        instance = CourseInstance.objects.get(id=1)
        instance.course.teachers.add(self.user.userprofile)
        instance_url = instance.url
        instance_str = str(instance)
        visible = instance.visible_to_students
        assistant_names = self._as_names(instance.assistants)
        module_names = self._as_names(instance.course_modules)

        url = instance.get_url('course-clone')
        self.client.login(username='testUser', password='testPassword')
        response = self.client.post(url, { 'new_url': 'another' }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "alert alert-danger")
        self.assertContains(response, "alert alert-success")

        instance = CourseInstance.objects.get(id=1)
        self.assertEqual(instance.url, instance_url)
        self.assertEqual(str(instance), instance_str)
        self.assertEqual(instance.visible_to_students, visible)
        self.assertEqual(self._as_names(instance.assistants), assistant_names)
        self.assertEqual(self._as_names(instance.course_modules), module_names)

        new_instance = CourseInstance.objects.get(course=instance.course, url="another")
        self.assertEqual(str(new_instance), instance_str)
        self.assertFalse(new_instance.visible_to_students)
        self.assertEqual(self._as_names(new_instance.assistants), assistant_names)
        self.assertEqual(self._as_names(new_instance.course_modules), module_names)

        old_modules = list(instance.course_modules.all())
        new_modules = list(new_instance.course_modules.all())
        self.assertEqual(len(old_modules), len(new_modules))
        for i in range(len(old_modules)):
            self.assertEqual(old_modules[i].url, new_modules[i].url)
            self.assertEqual(
                self._as_names(old_modules[i].chapters),
                self._as_names(new_modules[i].chapters)
            )
            self.assertEqual(
                self._as_names(old_modules[i].learning_objects),
                self._as_names(new_modules[i].learning_objects)
            )
            self.assertEqual(
                self._as_class(old_modules[i].learning_objects),
                self._as_class(new_modules[i].learning_objects)
            )

    def _as_names(self, queryset):
        return self._as(queryset, lambda a: a.name)

    def _as_class(self, queryset):
        return self._as(queryset, lambda a: a.as_leaf_class().__class__)

    def _as(self, queryset, op):
        return list(op(a) for a in queryset.all())
