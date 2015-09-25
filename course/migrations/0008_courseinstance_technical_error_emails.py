# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0007_auto_20150828_1210'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseinstance',
            name='technical_error_emails',
            field=models.CharField(help_text='By default exercise errors are reported to teacher email addresses. Set this field to override the recipients.', max_length=255, blank=True),
            preserve_default=True,
        ),
    ]
