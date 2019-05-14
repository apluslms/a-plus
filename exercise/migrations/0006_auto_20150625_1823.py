# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    # Django 2.0: Because of a table alteration limitation of SQLite,
    # it is prohibited to perform RenameModel and RenameField operations on models
    # or fields referenced by other models in a transaction.
    # In order to allow migrations containing these operations to be applied,
    # you must set the Migration.atomic attribute to False.
    # This migration renames the table exercise_coursemodule to course_coursemodule
    # (model definition was moved from the exercise app to the course app).
    atomic = False

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
