# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0003_auto_20150617_0654'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='url',
            field=models.CharField(unique=True, help_text='Input an URL identifier for this course. Taken words include: admin, course', max_length=255, validators=[django.core.validators.RegexValidator(regex='^(?!admin$)(?!course$)[\\w\\-\\.]*$')]),
            preserve_default=True,
        ),
    ]
