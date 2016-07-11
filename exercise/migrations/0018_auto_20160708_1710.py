# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import lib.fields


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0017_auto_20160205_1026'),
    ]

    operations = [
        migrations.AddField(
            model_name='learningobject',
            name='exercise_info',
            field=lib.fields.JSONField(blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobject',
            name='model_answers',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
    ]
