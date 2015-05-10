# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='baseplugin',
            name='oauth_consumer',
        ),
        migrations.RemoveField(
            model_name='basetab',
            name='oauth_consumer',
        ),
    ]
