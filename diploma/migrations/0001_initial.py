# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import lib.models
import django.db.models.deletion
import diploma.models
import lib.fields


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0030_auto_20160912_1341'),
        ('userprofile', '0003_auto_20160728_1139'),
        ('exercise', '0024_auto_20160919_1951'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseDiplomaDesign',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('logo', models.ImageField(upload_to=diploma.models.build_upload_dir, null=True, blank=True)),
                ('title', models.TextField()),
                ('body', models.TextField()),
                ('date', models.CharField(max_length=256)),
                ('signature_name', models.CharField(max_length=256)),
                ('signature_title', models.CharField(max_length=256)),
                ('small_print', models.TextField()),
                ('point_limits', lib.fields.JSONField(help_text='A list of length 5 where each element is the required points for n:th grade.The element can be a list of 2-tuples [[difficulty_level_a, points],[difficulty_level_b, points]].', blank=True)),
                ('pad_points', models.BooleanField(default=False, help_text='If difficulty levels are used the lower level can be padded with higher level points.')),
                ('course', models.OneToOneField(null=True, to='course.CourseInstance', on_delete=django.db.models.deletion.SET_NULL)),
                ('exercises_to_pass', models.ManyToManyField(to='exercise.BaseExercise')),
                ('modules_to_pass', models.ManyToManyField(to='course.CourseModule')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StudentDiploma',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now=True)),
                ('hashkey', models.CharField(max_length=32, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('grade', models.PositiveIntegerField(default=0)),
                ('design', models.ForeignKey(to='diploma.CourseDiplomaDesign')),
                ('profile', models.ForeignKey(null=True, to='userprofile.UserProfile', on_delete=django.db.models.deletion.SET_NULL)),
            ],
            options={
            },
            bases=(lib.models.UrlMixin, models.Model),
        ),
    ]
