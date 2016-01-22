# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0002_auto_20150427_1717'),
        ('course', '0014_auto_20160106_1303'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseinstance',
            name='students',
            field=models.ManyToManyField(blank=True, related_name='enrolled', to='userprofile.UserProfile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='submission_access',
            field=models.IntegerField(choices=[(1, 'Internal and external users'), (2, 'Only external users'), (3, 'Only internal users')], default=3),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='view_access',
            field=models.IntegerField(choices=[(0, 'Public to internet'), (1, 'Internal and external users'), (2, 'Only external users'), (3, 'Only internal users')], default=3),
            preserve_default=True,
        ),
    ]
