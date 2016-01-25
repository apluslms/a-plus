# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


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
    ]
