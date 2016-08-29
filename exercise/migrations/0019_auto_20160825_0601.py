# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0018_auto_20160708_1710'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learningobject',
            name='model_answers',
            field=models.TextField(help_text='List model answer files as protected URL addresses.', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='learningobject',
            name='status',
            field=models.CharField(choices=[('enrollment', 'Enrollment questions'), ('enrollment_ext', 'Enrollment questions for external students'), ('hidden', 'Hidden from non course staff'), ('maintenance', 'Maintenance'), ('ready', 'Ready'), ('unlisted', 'Unlisted in table of contents')], default='ready', max_length=32),
            preserve_default=True,
        ),
    ]
