# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0025_auto_20170215_0953'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='baseexercise',
            name='confirm_the_level',
        ),
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=models.CharField(choices=[('error', 'Error'), ('initialized', 'Initialized'), ('ready', 'Ready'), ('rejected', 'Rejected'), ('unofficial', 'Unofficial'), ('waiting', 'In grading')], max_length=32, default='initialized'),
            preserve_default=True,
        ),
    ]
