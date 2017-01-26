# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0026_auto_20160809_1551'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseinstance',
            name='head_urls',
            field=models.TextField(blank=True, help_text='External CSS and JS resources that are included on all course pages. Separate with white space.'),
            preserve_default=True,
        ),
    ]
