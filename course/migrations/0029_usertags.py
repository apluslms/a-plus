# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import lib.models
import colorfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0003_auto_20160728_1139'),
        ('course', '0028_auto_20160825_0601'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserTag',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.CharField(blank=True, max_length=164, help_text='Describe the usage or meaning of this usertag')),
                ('visible_to_students', models.BooleanField(default=False)),
                ('color', colorfield.fields.ColorField(default='#CD0000', help_text='Color that is used for this tag.', max_length=10)),
                ('course_instance', models.ForeignKey(related_name='usertags', to='course.CourseInstance', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(lib.models.UrlMixin, models.Model),
        ),
        migrations.CreateModel(
            name='UserTagging',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('course_instance', models.ForeignKey(related_name='taggings', to='course.CourseInstance', on_delete=models.CASCADE)),
                ('tag', models.ForeignKey(related_name='taggings', to='course.UserTag', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(related_name='taggings', to='userprofile.UserProfile', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='usertagging',
            unique_together=set([('tag', 'user', 'course_instance')]),
        ),
        migrations.AlterIndexTogether(
            name='usertagging',
            index_together=set([('user', 'course_instance')]),
        ),
    ]
