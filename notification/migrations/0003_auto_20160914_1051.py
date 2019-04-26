# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0002_auto_20160912_1341'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='submission',
            field=models.ForeignKey(blank=True, related_name='notifications', null=True, to='exercise.Submission', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
