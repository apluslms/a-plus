# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0008_courseinstance_technical_error_emails'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseinstance',
            name='technical_error_emails',
            field=models.CharField(max_length=255, blank=True, help_text='By default exercise errors are reported to teacher email addresses. Set this field as comma separated emails to override the recipients.'),
            preserve_default=True,
        ),
    ]
