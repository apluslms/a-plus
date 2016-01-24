# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CourseRepo',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('key', models.SlugField(unique=True)),
                ('git_origin', models.CharField(max_length=255)),
                ('git_branch', models.CharField(max_length=40)),
                ('update_hook', models.URLField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='CourseUpdate',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('request_ip', models.CharField(max_length=40)),
                ('request_time', models.DateTimeField(auto_now_add=True)),
                ('updated_time', models.DateTimeField(auto_now=True)),
                ('updated', models.BooleanField(default=False)),
                ('log', models.TextField(default='')),
                ('course_repo', models.ForeignKey(to='gitmanager.CourseRepo', related_name='updates')),
            ],
        ),
    ]
