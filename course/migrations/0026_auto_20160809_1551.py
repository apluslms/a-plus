# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0025_auto_20160728_1139'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseinstance',
            name='enrollment_ending_time',
            field=models.DateTimeField(blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='enrollment_starting_time',
            field=models.DateTimeField(blank=True, null=True),
            preserve_default=True,
        ),
    ]
