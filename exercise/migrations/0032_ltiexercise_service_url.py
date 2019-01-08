# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from urllib.parse import urljoin, urlsplit
from django.db import migrations, models

def forwards(apps, schema_editor):
    LTIExercise = apps.get_model('exercise', 'LTIExercise')
    exercises = (LTIExercise.objects.all()
                 .exclude(service_url=None)
                 .exclude(service_url=''))
    errors = []
    for exercise in exercises:
        uri1 = urlsplit(exercise.service_url)
        uri2 = urlsplit(exercise.lti_service.url)
        if uri1.netloc and uri1.netloc != uri2.netloc:
            errors.append(exercise)
    if errors:
        print()
        msg = ['Database is in inconsistent state.']
        for exercise in errors:
            msg.append("  LTIExercise(pk=%s): %s <> %s" % (exercise.pk, exercise.service_url, exercise.lti_service.url))
        msg.append("For above exercises, domain in LTIExercise.service_url doesn't match domain in LTIExercise.lti_service.url.")
        msg.append("Database is in inconsistent state. Manual fixing is required.")
        raise RuntimeError('\n'.join(msg))
    for exercise in exercises:
        uri = urlsplit(exercise.service_url)
        url = uri._replace(scheme='', netloc='').geturl()
        exercise.service_url = url
        exercise.save(update_fields=['service_url'])

def backwards(apps, schema_editor):
    LTIExercise = apps.get_model('exercise', 'LTIExercise')
    for exercise in LTIExercise.objects.all():
        exercise.service_url = urljoin(exercise.lti_service.url, exercise.service_url)
        exercise.save(update_fields=['service_url'])

class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('exercise', '0031_exercisecollection'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
