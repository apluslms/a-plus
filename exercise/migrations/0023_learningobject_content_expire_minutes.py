# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0022_auto_20160906_1401'),
    ]

    operations = [
        migrations.AddField(
            model_name='learningobject',
            name='content_expire_minutes',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
    ]
