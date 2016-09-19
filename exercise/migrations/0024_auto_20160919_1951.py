# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0023_learningobject_content_expire_minutes'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='submission',
            options={'ordering': ['-id']},
        ),
        migrations.RemoveField(
            model_name='learningobject',
            name='content_expire_minutes',
        ),
        migrations.RemoveField(
            model_name='learningobject',
            name='content_head',
        ),
        migrations.RemoveField(
            model_name='learningobject',
            name='content_stamp',
        ),
        migrations.RemoveField(
            model_name='learningobject',
            name='content_time',
        ),
    ]
