# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='EmbeddedTab',
            new_name='ExternalEmbeddedTab',
        ),
        migrations.AlterField(
            model_name='basetab',
            name='label',
            field=models.CharField(help_text='Label is the word displayed on the tab.', max_length=12),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='basetab',
            name='title',
            field=models.CharField(help_text='Title is displayed on the top of the tab page.', max_length=64),
            preserve_default=True,
        ),
    ]
