# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0005_auto_20150625_1821'),
    ]

    database_operations = [
        migrations.AlterModelTable('CourseModule', 'course_coursemodule'),
        migrations.AlterModelTable('LearningObjectCategory', 'course_learningobjectcategory'),
        migrations.AlterModelTable('DeadlineRuleDeviation', 'deviations_deadlineruledeviation'),
        migrations.AlterModelTable('MaxSubmissionsRuleDeviation', 'deviations_maxsubmissionsruledeviation'),
    ]

    state_operations = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=database_operations,
            state_operations=state_operations)
    ]