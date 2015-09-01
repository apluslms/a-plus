# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import course.models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0006_auto_20150721_1152'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseinstance',
            name='website',
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='description',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='image',
            field=models.ImageField(null=True, upload_to=course.models.build_upload_dir, blank=True),
            preserve_default=True,
        ),
    ]
