# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0027_courseinstance_head_urls'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseinstance',
            name='content_numbering',
            field=models.IntegerField(choices=[(0, 'No numbering'), (1, 'Arabic'), (2, 'Roman'), (3, 'Hidden arabic')], default=1),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='courseinstance',
            name='index_mode',
            field=models.IntegerField(choices=[(0, 'User results'), (1, 'Table of contents'), (2, 'Link last visited content'), (10, 'Experimental setup (hard-coded)')], help_text='Select content for the course index page.', default=0),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='coursemodule',
            name='status',
            field=models.CharField(choices=[('hidden', 'Hidden'), ('maintenance', 'Maintenance'), ('ready', 'Ready'), ('unlisted', 'Unlisted in table of contents')], default='ready', max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='learningobjectcategory',
            name='status',
            field=models.CharField(choices=[('hidden', 'Hidden'), ('ready', 'Ready')], default='ready', max_length=32),
            preserve_default=True,
        ),
    ]
