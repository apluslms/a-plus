# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0002_auto_20150427_1717'),
        ('course', '0020_auto_20160615_1239'),
    ]

    operations = [
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('personal_code', models.CharField(max_length=10, blank=True, default='')),
                ('course_instance', models.ForeignKey(to='course.CourseInstance', on_delete=models.CASCADE)),
                ('user_profile', models.ForeignKey(to='userprofile.UserProfile', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='students2',
            field=models.ManyToManyField(to='userprofile.UserProfile', through='course.Enrollment', related_name='enrolled', blank=True),
            preserve_default=True,
        ),
    ]
