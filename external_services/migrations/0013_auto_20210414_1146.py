# Generated by Django 2.2.20 on 2021-04-14 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('external_services', '0012_auto_20201202_1856'),
    ]

    operations = [
        migrations.AlterField(
            model_name='menuitem',
            name='menu_icon_class',
            field=models.CharField(blank=True, help_text='Menu icon style name (else service default), e.g. star see https://getbootstrap.com/docs/3.4/components/#glyphicons', max_length=32, null=True),
        ),
    ]
