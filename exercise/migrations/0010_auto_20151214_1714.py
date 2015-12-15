# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0009_auto_20150721_1152'),
    ]

    operations = [
        migrations.RenameField(
            model_name='learningobject',
            old_name='instructions',
            new_name='content',
        ),
        migrations.AddField(
            model_name='learningobject',
            name='content_time',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
