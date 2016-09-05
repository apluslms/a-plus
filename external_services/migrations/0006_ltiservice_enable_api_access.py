# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('external_services', '0005_auto_20160829_1344'),
    ]

    operations = [
        migrations.AddField(
            model_name='ltiservice',
            name='enable_api_access',
            field=models.BooleanField(help_text="Enable sharing user's api token and course api url in lti launch request. This grants api access with user's privileges for the lti tool.", default=False),
            preserve_default=True,
        ),
    ]
