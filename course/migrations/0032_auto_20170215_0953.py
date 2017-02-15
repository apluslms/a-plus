# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0031_courseinstance_build_log_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learningobjectcategory',
            name='status',
            field=models.CharField(default='ready', choices=[('hidden', 'Hidden'), ('nototal', 'No total points'), ('ready', 'Ready')], max_length=32),
            preserve_default=True,
        ),
    ]
