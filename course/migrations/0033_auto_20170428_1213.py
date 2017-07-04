# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0032_auto_20170215_0953'),
    ]

    operations = [
        migrations.AddField(
            model_name='learningobjectcategory',
            name='accept_unofficial_submits',
            field=models.BooleanField(help_text='Grade unofficial submits after deadlines have passed. The points are stored but not included in official records.', default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobjectcategory',
            name='confirm_the_level',
            field=models.BooleanField(help_text='Once exercise is graded non zero it confirms all the points on the hierarchy level. Implemented as a mandatory feedback feature.', default=False),
            preserve_default=True,
        ),
    ]
