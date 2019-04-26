# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0002_auto_20150427_1717'),
        ('exercise', '0014_ltiexercise'),
    ]

    operations = [
        migrations.CreateModel(
            name='LearningObjectDisplay',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('learning_object', models.ForeignKey(to='exercise.LearningObject', on_delete=models.CASCADE)),
                ('profile', models.ForeignKey(to='userprofile.UserProfile', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='learningobject',
            name='status',
            field=models.CharField(choices=[('ready', 'Ready'), ('unlisted', 'Unlisted in table of contents'), ('enrollment', 'Enrollment questions'), ('hidden', 'Hidden from non course staff'), ('maintenance', 'Maintenance')], max_length=32, default='ready'),
            preserve_default=True,
        ),
    ]
