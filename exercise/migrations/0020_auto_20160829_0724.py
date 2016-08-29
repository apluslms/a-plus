# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0019_auto_20160825_0601'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=models.CharField(default='initialized', choices=[('error', 'Error'), ('initialized', 'Initialized'), ('ready', 'Ready'), ('waiting', 'Waiting')], max_length=32),
            preserve_default=True,
        ),
    ]
