# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0010_auto_20151214_1714'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursechapter',
            name='parent',
            field=models.ForeignKey(to='course.CourseChapter', blank=True, null=True, related_name='children', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='coursechapter',
            unique_together=set([]),
        ),
    ]
