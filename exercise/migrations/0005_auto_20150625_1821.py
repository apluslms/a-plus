# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0004_auto_20150617_1033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursemodule',
            name='closing_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='coursemodule',
            name='late_submission_deadline',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='coursemodule',
            name='opening_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='deadlineruledeviation',
            name='exercise',
            field=models.ForeignKey(to='exercise.BaseExercise'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='maxsubmissionsruledeviation',
            name='exercise',
            field=models.ForeignKey(to='exercise.BaseExercise'),
            preserve_default=True,
        ),
    ]
