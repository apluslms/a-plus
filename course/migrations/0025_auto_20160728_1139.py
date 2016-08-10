# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0003_auto_20160728_1139'),
        ('course', '0024_auto_20160726_1232'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('course_instance', models.ForeignKey(related_name='groups', to='course.CourseInstance')),
                ('members', models.ManyToManyField(to='userprofile.UserProfile', related_name='groups')),
            ],
            options={
                'ordering': ['course_instance', 'timestamp'],
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='selected_group',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, default=None, blank=True, to='course.StudentGroup'),
            preserve_default=True,
        ),
    ]
