# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0002_auto_20150427_1717'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='url',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], help_text='Input an URL identifier for this course.', unique=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='courseinstance',
            name='url',
            field=models.CharField(max_length=255, validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], help_text='Input an URL identifier for this course instance.'),
            preserve_default=True,
        ),
    ]
