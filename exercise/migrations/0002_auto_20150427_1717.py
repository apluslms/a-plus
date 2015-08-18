# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=models.CharField(choices=[('initialized', 'Initialized'), ('waiting', 'Waiting'), ('ready', 'Ready'), ('error', 'Error')], default='initialized', max_length=32),
            preserve_default=True,
        ),
    ]
