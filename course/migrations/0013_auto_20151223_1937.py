# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0012_auto_20151218_0857'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='learningobjectcategory',
            name='hidden_to',
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='configure_url',
            field=models.URLField(blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseinstance',
            name='language',
            field=models.CharField(max_length=5, default='en'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobjectcategory',
            name='status',
            field=models.CharField(choices=[('ready', 'Ready'), ('hidden', 'Hidden')], max_length=32, default='ready'),
            preserve_default=True,
        ),
    ]
