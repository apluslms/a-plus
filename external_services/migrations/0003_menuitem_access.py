# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('external_services', '0002_auto_20150427_1717'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuitem',
            name='access',
            field=models.IntegerField(choices=[(0, 'All students, assistants and teachers can access.'), (5, 'Only assistants and teachers can access.'), (10, 'Only teachers can access.')], default=0),
            preserve_default=True,
        ),
    ]
