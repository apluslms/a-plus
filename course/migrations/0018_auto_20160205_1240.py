# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0017_enroll_submitters'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseinstance',
            name='language',
            field=models.CharField(blank=True, max_length=5, default=None),
            preserve_default=True,
        ),
    ]
