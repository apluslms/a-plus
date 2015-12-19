# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


def url_from_id(apps, schema_editor):
    Model = apps.get_model('exercise', 'LearningObject')
    for row in Model.objects.all():
        row.url = str(row.id)
        row.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0011_auto_20151218_0857'),
    ]

    operations = [

        migrations.RunPython(url_from_id, reverse_code=noop),

        migrations.AlterField(
            model_name='learningobject',
            name='url',
            field=models.CharField(validators=[django.core.validators.RegexValidator(regex='^[\\w\\-\\.]*$')], max_length=255, help_text='Input an URL identifier for this object.'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='learningobject',
            unique_together=set([('course_module', 'parent', 'url')]),
        ),
    ]
