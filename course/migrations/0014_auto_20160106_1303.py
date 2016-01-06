# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0013_auto_20151223_1937'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='coursemodule',
            options={'ordering': ['order', 'closing_time', 'id']},
        ),
        migrations.AlterField(
            model_name='courseinstance',
            name='module_numbering',
            field=models.IntegerField(choices=[(0, 'No numbering'), (1, 'Arabic'), (2, 'Roman'), (3, 'Hidden arabic')], default=1),
            preserve_default=True,
        ),
    ]
