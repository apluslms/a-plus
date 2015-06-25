# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0006_auto_20150625_1823'),
        ('course', '0005_auto_20150625_1835'),
        ('deviations', '0001_initial')
    ]

    operations = [
        migrations.AlterField(
            model_name='learningobject',
            name='category',
            field=models.ForeignKey(related_name='learning_objects', to='course.LearningObjectCategory'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='learningobject',
            name='course_module',
            field=models.ForeignKey(related_name='learning_objects', to='course.CourseModule'),
            preserve_default=True,
        ),
    ]
