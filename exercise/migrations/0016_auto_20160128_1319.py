# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0015_auto_20160124_2139'),
    ]

    operations = [
        migrations.AddField(
            model_name='ltiexercise',
            name='aplus_get_and_post',
            field=models.BooleanField(help_text='Perform GET and POST from A+ with LTI data appended.', default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='ltiexercise',
            name='context_id',
            field=models.CharField(blank=True, max_length=128, help_text='Default: [hostname]/[course:url]/[instance:url]/'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='ltiexercise',
            name='resource_link_id',
            field=models.CharField(blank=True, max_length=128, help_text='Default: [aplusexercise:id]'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='ltiexercise',
            name='resource_link_title',
            field=models.CharField(blank=True, max_length=128, help_text='Default: Launch exercise'),
            preserve_default=True,
        ),
    ]
