# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0011_auto_20151215_1133'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coursechapter',
            name='course_module',
        ),
        migrations.RemoveField(
            model_name='coursechapter',
            name='parent',
        ),
        migrations.DeleteModel(
            name='CourseChapter',
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='content_numbering',
            field=models.IntegerField(choices=[(0, 'No numbering'), (1, 'Arabic'), (2, 'Roman')], default=1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='footer',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='index_mode',
            field=models.IntegerField(choices=[(0, 'User results'), (1, 'Table of contents')], help_text='Select content for the course index page.', default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='module_numbering',
            field=models.IntegerField(choices=[(0, 'No numbering'), (1, 'Arabic'), (2, 'Roman')], default=1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='coursemodule',
            name='status',
            field=models.CharField(choices=[('ready', 'Ready'), ('hidden', 'Hidden'), ('maintenance', 'Maintenance')], max_length=32, default='ready'),
            preserve_default=True,
        ),
    ]
