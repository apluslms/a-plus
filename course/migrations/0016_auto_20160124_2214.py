# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0015_auto_20160121_1544'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseinstance',
            name='submission_access',
        ),
        migrations.RemoveField(
            model_name='courseinstance',
            name='view_access',
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='enrollment_audience',
            field=models.IntegerField(choices=[(1, 'Internal users'), (2, 'External users'), (3, 'Internal and external users')], default=1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='view_content_to',
            field=models.IntegerField(choices=[(1, 'Enrolled students'), (2, 'Enrollment audience'), (3, 'All registered users'), (4, 'Public to internet')], default=2),
            preserve_default=True,
        ),
    ]
