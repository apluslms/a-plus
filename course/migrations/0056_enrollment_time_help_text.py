# Generated by Django 3.2.13 on 2022-08-16 07:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0055_alter_enrollment_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseinstance',
            name='enrollment_ending_time',
            field=models.DateTimeField(blank=True, help_text='COURSE_INSTANCE_ENROLLMENT_TIME_HELPTEXT', null=True, verbose_name='LABEL_ENROLLMENT_ENDING_TIME'),
        ),
        migrations.AlterField(
            model_name='courseinstance',
            name='enrollment_starting_time',
            field=models.DateTimeField(blank=True, help_text='COURSE_INSTANCE_ENROLLMENT_TIME_HELPTEXT', null=True, verbose_name='LABEL_ENROLLMENT_STARTING_TIME'),
        ),
    ]
