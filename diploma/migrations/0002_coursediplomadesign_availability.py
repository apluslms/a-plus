# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('diploma', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursediplomadesign',
            name='availability',
            field=models.IntegerField(choices=[(1, 'Internal users'), (2, 'External users'), (3, 'Internal and external users')], default=2),
            preserve_default=True,
        ),
    ]
