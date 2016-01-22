# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0012_auto_20151218_0858'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='learningobject',
            unique_together=set([('course_module', 'parent', 'url')]),
        ),
        migrations.AlterField(
            model_name='learningobject',
            name='status',
            field=models.CharField(default='ready', max_length=32, choices=[('ready', 'Ready'), ('unlisted', 'Unlisted in table of contents'), ('hidden', 'Hidden from non course staff'), ('maintenance', 'Maintenance')]),
            preserve_default=True,
        ),
    ]
