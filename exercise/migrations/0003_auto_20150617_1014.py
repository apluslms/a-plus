# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import lib.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0002_auto_20150427_1717'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AsynchronousExercise',
        ),
        migrations.DeleteModel(
            name='SynchronousExercise',
        ),
        migrations.AlterModelOptions(
            name='learningobject',
            options={'ordering': ['order', 'id']},
        ),
        migrations.AddField(
            model_name='coursemodule',
            name='chapter',
            field=models.IntegerField(default=1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='coursemodule',
            name='content_url',
            field=models.URLField(blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='coursemodule',
            name='subchapter',
            field=models.IntegerField(default=1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='coursemodule',
            name='url',
            field=models.CharField(max_length=255, null=True, help_text='Input an URL identifier for this module. Taken words include: teachers, user', default=None, validators=[django.core.validators.RegexValidator(regex='^(?!teachers$)(?!user$)[\\w\\-\\.]*$')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submission',
            name='late_penalty_applied',
            field=lib.fields.PercentField(blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='learningobject',
            name='order',
            field=models.IntegerField(default=1),
            preserve_default=True,
        ),
    ]
