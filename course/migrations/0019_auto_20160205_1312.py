# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0018_auto_20160205_1240'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseinstance',
            name='language',
            field=models.CharField(blank=True, default='', max_length=5),
            preserve_default=True,
        ),
    ]
