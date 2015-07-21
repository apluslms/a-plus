# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0008_auto_20150625_1844'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='baseexercise',
            options={},
        ),
        migrations.AlterModelOptions(
            name='learningobject',
            options={'ordering': ['course_module', 'order', 'id']},
        ),
    ]
