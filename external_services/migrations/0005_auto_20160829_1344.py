# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('external_services', '0004_auto_20150828_1210'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuitem',
            name='menu_group_label',
            field=models.CharField(blank=True, null=True, max_length=32, help_text='Places menu item under a group label.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='menuitem',
            name='menu_url',
            field=models.CharField(blank=True, null=True, max_length=256, help_text='A link URL (else service default). Relative URLs are relative to course root.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='course_instance',
            field=models.ForeignKey(help_text='A course where the menu item exists.', to='course.CourseInstance', related_name='ext_services'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='menu_icon_class',
            field=models.CharField(blank=True, null=True, max_length=32, help_text='Menu icon style name (else service default), e.g. star see http://getbootstrap.com/components/#glyphicons-glyphs'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='menu_label',
            field=models.CharField(blank=True, null=True, max_length=32, help_text='Label for the menu link (else service default).'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='service',
            field=models.ForeignKey(help_text='If preconfigured, an external service to link.', to='external_services.LinkService', null=True, blank=True),
            preserve_default=True,
        ),
    ]
