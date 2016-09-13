# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0029_usertags'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='usertag',
            options={'ordering': ['course_instance', 'name']},
        ),
        migrations.AlterModelOptions(
            name='usertagging',
            options={'ordering': ['tag']},
        ),
    ]
