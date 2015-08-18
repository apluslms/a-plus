# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import lib.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0006_auto_20150625_1823'),
        ('userprofile', '0002_auto_20150427_1717'),
        ('inheritance', '0001_initial'),
        ('course', '0004_auto_20150625_1821'),
    ]

    state_operations = [
        migrations.CreateModel(
            name='CourseModule',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('url', models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(regex='^(?!teachers$)(?!user$)[\\w\\-\\.]*$')], help_text='Input an URL identifier for this module. Taken words include: teachers, user')),
                ('chapter', models.IntegerField(default=1)),
                ('subchapter', models.IntegerField(default=1)),
                ('points_to_pass', models.PositiveIntegerField(default=0)),
                ('introduction', models.TextField(blank=True)),
                ('opening_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('closing_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('content_url', models.URLField(blank=True)),
                ('late_submissions_allowed', models.BooleanField(default=False)),
                ('late_submission_deadline', models.DateTimeField(default=django.utils.timezone.now)),
                ('late_submission_penalty', lib.fields.PercentField(default=0.5, help_text='Multiplier of points to reduce, as decimal. 0.1 = 10%')),
                ('course_instance', models.ForeignKey(related_name='course_modules', to='course.CourseInstance')),
            ],
            options={
                'ordering': ['closing_time', 'id'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LearningObjectCategory',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=35)),
                ('description', models.TextField(blank=True)),
                ('points_to_pass', models.PositiveIntegerField(default=0)),
                ('course_instance', models.ForeignKey(related_name='categories', to='course.CourseInstance')),
                ('hidden_to', models.ManyToManyField(blank=True, related_name='hidden_categories', null=True, to='userprofile.UserProfile')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='learningobjectcategory',
            unique_together=set([('name', 'course_instance')]),
        ),
        migrations.AlterUniqueTogether(
            name='coursemodule',
            unique_together=set([('course_instance', 'url')]),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=state_operations)
    ]
