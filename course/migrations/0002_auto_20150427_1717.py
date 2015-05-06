# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='url',
            field=models.CharField(validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], max_length=255, help_text="Input an identifier for this course's URL.", unique=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='coursehook',
            name='hook_type',
            field=models.CharField(choices=[('post-grading', 'Post grading')], default='post-grading', max_length=12),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='courseinstance',
            name='url',
            field=models.CharField(validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], help_text='Input an URL identifier for this course.', max_length=255),
            preserve_default=True,
        ),
    ]
