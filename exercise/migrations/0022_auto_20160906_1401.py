# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0021_auto_20160905_1335'),
    ]

    operations = [
        migrations.AlterField(
            model_name='baseexercise',
            name='difficulty',
            field=models.CharField(blank=True, max_length=32),
            preserve_default=True,
        ),
    ]
