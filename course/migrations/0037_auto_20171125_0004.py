# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-11-24 22:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0036_auto_20170907_1537'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursehook',
            name='password',
            field=models.CharField(blank=True, help_text='Basic access authentication', max_length=128),
        ),
        migrations.AddField(
            model_name='coursehook',
            name='username',
            field=models.CharField(blank=True, help_text='Basic access authentication', max_length=128),
        ),
        migrations.AlterField(
            model_name='coursehook',
            name='hook_type',
            field=models.CharField(choices=[('post-grading', 'Post grading'), ('xapi', 'xAPI logging to remote LRS')], default='post-grading', max_length=12),
        ),
    ]
