# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0007_auto_20150625_1835'),
    ]

    state_operations = [
        migrations.DeleteModel(name='CourseModule'),
        migrations.DeleteModel(name='LearningObjectCategory'),
        migrations.DeleteModel(name='DeadlineRuleDeviation'),
        migrations.DeleteModel(name='MaxSubmissionsRuleDeviation'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=state_operations)
    ]
