# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0016_auto_20160128_1319'),
    ]

    operations = [
        migrations.AddField(
            model_name='baseexercise',
            name='allow_assistant_viewing',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='ltiexercise',
            name='aplus_get_and_post',
            field=models.BooleanField(default=False, help_text='Perform GET and POST from A+ to custom service URL with LTI data appended.'),
            preserve_default=True,
        ),
    ]
