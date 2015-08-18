# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
from django.utils.text import slugify


def url_from_name(apps, schema_editor):
    Model = apps.get_model('exercise', 'CourseModule')
    for row in Model.objects.all():
        row.url = slugify(row.name)
        row.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0003_auto_20150617_1014'),
    ]

    operations = [
        
        migrations.RunPython(url_from_name, reverse_code=noop),
        
        migrations.AlterField(
            model_name='coursemodule',
            name='url',
            field=models.CharField(validators=[django.core.validators.RegexValidator(regex='^(?!teachers$)(?!user$)[\\w\\-\\.]*$')], max_length=255, help_text='Input an URL identifier for this module. Taken words include: teachers, user'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='coursemodule',
            unique_together=set([('course_instance', 'url')]),
        ),
    ]
