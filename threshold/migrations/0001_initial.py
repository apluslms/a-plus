# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0032_auto_20170215_0953'),
        ('exercise', '0025_auto_20170215_0953'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseModuleRequirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('negative', models.BooleanField(default=False)),
                ('module', models.ForeignKey(to='course.CourseModule', related_name='requirements', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Threshold',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('consume_harder_points', models.BooleanField(help_text='Harder points are consumed by easier difficulty requirements.', default=False)),
                ('course_instance', models.ForeignKey(to='course.CourseInstance', related_name='thresholds', on_delete=models.CASCADE)),
                ('passed_categories', models.ManyToManyField(blank=True, to='course.LearningObjectCategory')),
                ('passed_exercises', models.ManyToManyField(blank=True, to='exercise.BaseExercise')),
                ('passed_modules', models.ManyToManyField(blank=True, to='course.CourseModule')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ThresholdPoints',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('limit', models.PositiveIntegerField()),
                ('difficulty', models.CharField(blank=True, max_length=32)),
                ('order', models.PositiveIntegerField(default=1)),
                ('threshold', models.ForeignKey(to='threshold.Threshold', related_name='points', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['threshold', 'order'],
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='coursemodulerequirement',
            name='threshold',
            field=models.ForeignKey(to='threshold.Threshold', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
