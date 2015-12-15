# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0009_auto_20151013_1434'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursechapter',
            name='content',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='coursechapter',
            name='content_time',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
