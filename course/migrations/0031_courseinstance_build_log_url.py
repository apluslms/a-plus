# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0030_auto_20160912_1341'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseinstance',
            name='build_log_url',
            field=models.URLField(blank=True),
            preserve_default=True,
        ),
    ]
