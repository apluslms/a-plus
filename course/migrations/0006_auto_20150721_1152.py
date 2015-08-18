# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0005_auto_20150625_1835'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseChapter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('order', models.IntegerField(default=1)),
                ('name', models.CharField(max_length=255)),
                ('url', models.CharField(help_text='Input an URL identifier for this chapter.', validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], max_length=255)),
                ('content_url', models.URLField(help_text='The resource to show.')),
                ('course_module', models.ForeignKey(related_name='chapters', to='course.CourseModule')),
            ],
            options={
                'ordering': ['course_module', 'order', 'id'],
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='coursechapter',
            unique_together=set([('course_module', 'url')]),
        ),
        migrations.AlterModelOptions(
            name='coursemodule',
            options={'ordering': ['closing_time', 'order', 'id']},
        ),
        migrations.RenameField(
            model_name='coursemodule',
            old_name='chapter',
            new_name='order',
        ),
        migrations.RemoveField(
            model_name='coursemodule',
            name='content_url',
        ),
        migrations.RemoveField(
            model_name='coursemodule',
            name='subchapter',
        ),
        migrations.AlterField(
            model_name='course',
            name='url',
            field=models.CharField(unique=True, validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], max_length=255, help_text='Input an URL identifier for this course.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='coursemodule',
            name='url',
            field=models.CharField(help_text='Input an URL identifier for this module.', validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], max_length=255),
            preserve_default=True,
        ),
    ]
