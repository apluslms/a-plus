# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0019_auto_20160205_1312'),
    ]

    operations = [
        migrations.AlterField(
            model_name='learningobjectcategory',
            name='name',
            field=models.CharField(max_length=255),
            preserve_default=True,
        ),
    ]
