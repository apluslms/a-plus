# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import lib.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CourseModule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('points_to_pass', models.PositiveIntegerField(default=0)),
                ('introduction', models.TextField(blank=True)),
                ('opening_time', models.DateTimeField(default=datetime.datetime.now)),
                ('closing_time', models.DateTimeField(default=datetime.datetime.now)),
                ('late_submissions_allowed', models.BooleanField(default=False)),
                ('late_submission_deadline', models.DateTimeField(default=datetime.datetime.now)),
                ('late_submission_penalty', lib.fields.PercentField(default=0.5, help_text='Multiplier of points to reduce, as decimal. 0.1 = 10%')),
            ],
            options={
                'ordering': ['closing_time', 'id'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DeadlineRuleDeviation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('extra_minutes', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
