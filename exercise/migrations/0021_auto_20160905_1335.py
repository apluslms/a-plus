# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0020_auto_20160829_0724'),
    ]

    operations = [
        migrations.AddField(
            model_name='baseexercise',
            name='confirm_the_level',
            field=models.BooleanField(default=False, help_text='Once this exercise is graded non zero it confirms all the points on this level. Implemented as a mandatory feedback feature.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='baseexercise',
            name='difficulty',
            field=models.CharField(max_length=32, default=''),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobject',
            name='audience',
            field=models.IntegerField(default=0, choices=[(0, 'Course audience'), (1, 'Only internal users'), (2, 'Only external users'), (3, 'Only registered users')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobject',
            name='content_stamp',
            field=models.CharField(max_length=128, blank=True),
            preserve_default=True,
        ),
    ]
