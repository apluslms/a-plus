# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0024_auto_20160919_1951'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learningobject',
            name='parent',
            field=models.ForeignKey(to='exercise.LearningObject', on_delete=django.db.models.deletion.SET_NULL, null=True, related_name='children', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=models.CharField(default='initialized', choices=[('error', 'Error'), ('initialized', 'Initialized'), ('ready', 'Ready'), ('waiting', 'In grading')], max_length=32),
            preserve_default=True,
        ),
    ]
