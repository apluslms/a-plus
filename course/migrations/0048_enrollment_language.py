# Generated by Django 2.2.13 on 2020-07-28 08:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0047_delete_duplicate_enrollments'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='language',
            field=models.CharField(blank=True, default='', max_length=5),
        ),
    ]
