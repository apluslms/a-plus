# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import diploma.models
import lib.models
import lib.fields


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0024_auto_20160919_1951'),
        ('course', '0030_auto_20160912_1341'),
        ('userprofile', '0003_auto_20160728_1139'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseDiplomaDesign',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('logo', models.ImageField(null=True, blank=True, upload_to=diploma.models.build_upload_dir)),
                ('title', models.TextField(blank=True)),
                ('body', models.TextField(blank=True)),
                ('date', models.CharField(max_length=256)),
                ('signature_name', models.CharField(blank=True, max_length=256)),
                ('signature_title', models.CharField(blank=True, max_length=256)),
                ('small_print', models.TextField(blank=True)),
                ('point_limits', lib.fields.JSONField(blank=True, help_text='A list of length 5 where each element is the required points for n:th grade.The element can be a list of 2-tuples [[difficulty_level_a, points],[difficulty_level_b, points]].')),
                ('pad_points', models.BooleanField(help_text='If difficulty levels are used the lower level can be padded with higher level points.', default=False)),
                ('course', models.OneToOneField(on_delete=django.db.models.deletion.SET_NULL, to='course.CourseInstance', null=True)),
                ('exercises_to_pass', models.ManyToManyField(blank=True, to='exercise.BaseExercise')),
                ('modules_to_pass', models.ManyToManyField(blank=True, to='course.CourseModule')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StudentDiploma',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now=True)),
                ('hashkey', models.CharField(unique=True, max_length=32)),
                ('name', models.CharField(max_length=255)),
                ('grade', models.PositiveIntegerField(default=0)),
                ('design', models.ForeignKey(to='diploma.CourseDiplomaDesign', on_delete=models.CASCADE)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='userprofile.UserProfile', null=True)),
            ],
            options={
            },
            bases=(lib.models.UrlMixin, models.Model),
        ),
    ]
