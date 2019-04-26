# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0010_auto_20151214_1714'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseChapter',
            fields=[
                ('learningobject_ptr', models.OneToOneField(
                    to='exercise.LearningObject', on_delete=models.CASCADE,
                    parent_link=True, primary_key=True, serialize=False, auto_created=True)),
                ('generate_table_of_contents', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=('exercise.learningobject',),
        ),
        migrations.AddField(
            model_name='learningobject',
            name='content_head',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobject',
            name='parent',
            field=models.ForeignKey(related_name='children', null=True, to='exercise.LearningObject', blank=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobject',
            name='status',
            field=models.CharField(choices=[('ready', 'Ready'), ('hidden', 'Hidden'), ('maintenance', 'Maintenance')], max_length=32, default='ready'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobject',
            name='url',
            field=models.CharField(max_length=255, help_text='Input an URL identifier for this object.', validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')],
            blank=True, null=True, default=None),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobject',
            name='use_wide_column',
            field=models.BooleanField(help_text='Remove the third info column for more space.', default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='learningobject',
            name='description',
            field=models.TextField(help_text='Internal description is not presented on site.', blank=True),
            preserve_default=True,
        ),
    ]
