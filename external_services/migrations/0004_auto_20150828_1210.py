# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('external_services', '0003_menuitem_access'),
    ]

    operations = [
        migrations.AlterField(
            model_name='linkservice',
            name='menu_icon_class',
            field=models.CharField(default='globe', help_text='A default menu icon style name, see http://getbootstrap.com/components/#glyphicons-glyphs', max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='menu_icon_class',
            field=models.CharField(null=True, help_text='Overrides service default menu icon style name, e.g. star see http://getbootstrap.com/components/#glyphicons-glyphs', blank=True, max_length=32),
            preserve_default=True,
        ),
    ]
