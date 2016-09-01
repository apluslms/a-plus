# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import lib.models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0028_auto_20160825_0601'),
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('audience', models.IntegerField(choices=[(1, 'Internal users'), (2, 'External users'), (3, 'Internal and external users')], default=3)),
                ('publish', models.DateTimeField(default=django.utils.timezone.now)),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('pin', models.BooleanField(default=False)),
                ('alert', models.CharField(choices=[('', 'No alert'), ('danger', 'Red / Danger'), ('info', 'Blue / Info'), ('success', 'Green / Success'), ('warning', 'Yellow / Warning')], max_length=8, blank=True, default='')),
                ('course_instance', models.ForeignKey(to='course.CourseInstance', related_name='news')),
            ],
            options={
                'ordering': ['course_instance', '-pin', '-publish'],
            },
            bases=(models.Model, lib.models.UrlMixin),
        ),
    ]
