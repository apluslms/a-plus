# Generated by Django 2.2.1 on 2019-08-08 11:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0044_auto_20190415_1807'),
    ]

    operations = [
        migrations.CreateModel(
            name='HardcodedUserTag',
            fields=[
            ],
            options={
                'proxy': True,
                'constraints': [],
                'indexes': [],
            },
            bases=('course.usertag',),
        ),
    ]
