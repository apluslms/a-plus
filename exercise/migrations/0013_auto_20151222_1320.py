# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0012_auto_20151218_0858'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learningobject',
            name='url',
            field=models.CharField(validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], max_length=255, help_text='Input an URL identifier for this object.'),
            preserve_default=True,
        ),
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
