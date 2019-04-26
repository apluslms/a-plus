# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0022_auto_20160906_1401'),
        ('notification', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='submission',
            field=models.ForeignKey(to='exercise.Submission', blank=True, null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='notification',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='sender',
            field=models.ForeignKey(related_name='sent_notifications', to='userprofile.UserProfile', blank=True, null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='subject',
            field=models.CharField(blank=True, max_length=255),
            preserve_default=True,
        ),
    ]
