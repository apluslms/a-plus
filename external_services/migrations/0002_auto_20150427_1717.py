# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('external_services', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='linkservice',
            name='enabled',
            field=models.BooleanField(help_text='If not enabled, the service is disabled for all course instances.', default=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='linkservice',
            name='menu_icon_class',
            field=models.CharField(help_text='A default menu icon style name, see http://getbootstrap.com/components/#glyphicons-glyphs', default='icon-globe', max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='linkservice',
            name='menu_label',
            field=models.CharField(help_text='A default label to show in the course menu.', max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='linkservice',
            name='url',
            field=models.CharField(help_text='The service URL', max_length=256),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='ltiservice',
            name='consumer_key',
            field=models.CharField(help_text='The consumer key provided by the LTI service.', max_length=128),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='ltiservice',
            name='consumer_secret',
            field=models.CharField(help_text='The consumer secret provided by the LTI service.', max_length=128),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='course_instance',
            field=models.ForeignKey(related_name='ext_services', help_text='A course instance where the service is used.', to='course.CourseInstance', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='menu_icon_class',
            field=models.CharField(null=True, blank=True, help_text='Overrides service default menu icon style, e.g. icon-star see http://getbootstrap.com/components/#glyphicons-glyphs', max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='menu_label',
            field=models.CharField(null=True, blank=True, help_text='Overrides service default label shown in the course menu.', max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='menu_weight',
            field=models.IntegerField(help_text='Heavier menu entries are placed after lighter ones.', default=0),
            preserve_default=True,
        ),
    ]
