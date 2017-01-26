# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0023_delete_students'),
    ]

    operations = [
        migrations.RenameField(
            model_name='courseinstance',
            old_name='students2',
            new_name='students',
        ),
    ]
