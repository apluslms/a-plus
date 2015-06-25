# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0006_auto_20150625_1823'),
        ('userprofile', '0002_auto_20150427_1717'),
    ]

    state_operations = [
        migrations.CreateModel(
            name='DeadlineRuleDeviation',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('extra_minutes', models.IntegerField()),
                ('exercise', models.ForeignKey(to='exercise.BaseExercise')),
                ('submitter', models.ForeignKey(to='userprofile.UserProfile')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MaxSubmissionsRuleDeviation',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('extra_submissions', models.IntegerField()),
                ('exercise', models.ForeignKey(to='exercise.BaseExercise')),
                ('submitter', models.ForeignKey(to='userprofile.UserProfile')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='maxsubmissionsruledeviation',
            unique_together=set([('exercise', 'submitter')]),
        ),
        migrations.AlterUniqueTogether(
            name='deadlineruledeviation',
            unique_together=set([('exercise', 'submitter')]),
        ),
    ]
    
    operations = [
        migrations.SeparateDatabaseAndState(state_operations=state_operations)
    ]
