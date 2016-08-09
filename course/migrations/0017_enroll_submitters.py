# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from course.models import CourseInstance


def enroll_submitters(apps, schema_editor):
    Model = apps.get_model('course', 'CourseInstance')
    for instance in Model.objects.all():
        instance.students = instance.get_submitted_profiles()
        instance.save()


def unenroll(apps, schema_editor):
    Model = apps.get_model('course', 'CourseInstance')
    for row in Model.objects.all():
        row.students.clear()
        row.save()


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0016_auto_20160124_2214'),
    ]

    operations = [
        migrations.RunPython(enroll_submitters, reverse_code=unenroll),
    ]
