# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0002_auto_20150427_1717'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentgroup',
            name='members',
        ),
        migrations.DeleteModel(
            name='StudentGroup',
        ),
    ]
