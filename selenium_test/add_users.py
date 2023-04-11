from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from course.models import CourseInstance

jenkins = User.objects.create(
    username="user",
    is_staff=True,
    is_superuser=True,
    first_name="Default",
    last_name="User",
)
jenkins.set_password("admin")
jenkins.save()

teacher = User.objects.create(
    username="teacher_user",
    password="admin",
    first_name="Teacher",
    last_name="User",
)
teacher.set_password("admin")
teacher.save()

assistant = User.objects.create(
    username="assistant_user",
    password="admin",
    first_name="Assistant",
    last_name="User",
)
assistant.set_password("admin")
assistant.save()

student = User.objects.create(
    username="student_user",
    password="admin",
    first_name="Student",
    last_name="User",
)
student.set_password("admin")
student.save()
student.userprofile.student_id = '123456'
student.userprofile.save()

instance = CourseInstance.objects.get(id=1)
instance.add_teacher(teacher.userprofile)
instance.add_assistant(assistant.userprofile)
instance.enroll_student(student)

instance2 = CourseInstance.objects.get(id=2)
instance2.add_teacher(teacher.userprofile)
instance2.enroll_student(student)
