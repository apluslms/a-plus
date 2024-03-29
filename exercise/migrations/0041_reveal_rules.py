# Generated by Django 3.2.4 on 2021-07-29 13:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exercise', '0040_submission_force_exercise_points'),
    ]

    operations = [
        migrations.CreateModel(
            name='RevealRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trigger', models.IntegerField(choices=[(1, 'TRIGGER_MANUAL'), (2, 'TRIGGER_IMMEDIATE'), (3, 'TRIGGER_TIME'), (4, 'TRIGGER_DEADLINE'), (5, 'TRIGGER_DEADLINE_ALL'), (6, 'TRIGGER_COMPLETION')], verbose_name='LABEL_TRIGGER')),
                ('delay_minutes', models.IntegerField(blank=True, null=True, verbose_name='LABEL_DELAY_MINUTES')),
                ('time', models.DateTimeField(blank=True, null=True, verbose_name='LABEL_TIME')),
                ('currently_revealed', models.BooleanField(default=False, verbose_name='LABEL_CURRENTLY_REVEALED')),
            ],
            options={
                'verbose_name': 'MODEL_NAME_REVEAL_RULE',
                'verbose_name_plural': 'MODEL_NAME_REVEAL_RULE_PLURAL',
            },
        ),
        migrations.AddField(
            model_name='baseexercise',
            name='model_solutions_reveal_rule',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='exercise.revealrule', verbose_name='LABEL_MODEL_SOLUTIONS_REVEAL_RULE'),
        ),
        migrations.AddField(
            model_name='baseexercise',
            name='submission_feedback_reveal_rule',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='exercise.revealrule', verbose_name='LABEL_SUBMISSION_FEEDBACK_REVEAL_RULE'),
        ),
    ]
