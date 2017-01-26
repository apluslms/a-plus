# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, connection
from course.models import Enrollment


def copy_enrollments(apps, schema_editor):
    Model = apps.get_model('course', 'Enrollment')
    cursor = connection.cursor()
    cursor.execute('select * from course_courseinstance_students')
    for row in cursor.fetchall():
        Model.objects.create(course_instance_id=row[1], user_profile_id=row[2])


def skip_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0021_auto_20160726_1209'),
    ]

    operations = [
        migrations.RunPython(copy_enrollments, reverse_code=skip_reverse),
    ]
