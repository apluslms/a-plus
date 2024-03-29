# Generated by Django 3.2.12 on 2022-08-11 10:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0045_auto_20220211_1540'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingSubmission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submission_time', models.DateTimeField(null=True, verbose_name='LABEL_SUBMISSION_TIME')),
                ('num_retries', models.PositiveIntegerField(default=0, verbose_name='LABEL_NUMBER_OF_RETRIES')),
                ('submission', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='exercise.submission', verbose_name='LABEL_SUBMISSION')),
            ],
            options={
                'verbose_name': 'MODEL_NAME_PENDING_SUBMISSION',
                'verbose_name_plural': 'MODEL_NAME_PENDING_SUBMISSION_PLURAL',
            },
        ),
    ]
