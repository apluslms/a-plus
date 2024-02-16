from django.db import migrations, models


def multiply_by_sixty(apps, schema_editor):
    DeadlineRuleDeviation = apps.get_model('deviations', 'DeadlineRuleDeviation')
    # Retrieve all instances of DeadlineRuleDeviation and update extra_seconds field
    for deviation in DeadlineRuleDeviation.objects.all():
        deviation.extra_seconds *= 60
        deviation.save()


class Migration(migrations.Migration):

    dependencies = [
        ('deviations', '0005_auto_20220211_1540'),
    ]

    operations = [
        migrations.RenameField(
            model_name='deadlineruledeviation',
            old_name='extra_minutes',
            new_name='extra_seconds',
        ),
        migrations.AlterField(
            model_name='deadlineruledeviation',
            name='extra_seconds',
            field=models.IntegerField(verbose_name='LABEL_EXTRA_SECONDS'),
        ),
        migrations.RunPython(multiply_by_sixty),
    ]
