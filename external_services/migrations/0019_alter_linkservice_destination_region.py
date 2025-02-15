# Generated by Django 4.2.12 on 2025-02-13 10:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('external_services', '0018_alter_menuitem_menu_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='linkservice',
            name='destination_region',
            field=models.PositiveSmallIntegerField(choices=[(0, 'DESTINATION_INTERNAL_PRIVACY_NOTICE'), (1, 'DESTINATION_ORGANIZATION_PRIVACY_NOTICE'), (3, 'DESTINATION_EEA_PRIVACY_NOTICE'), (5, 'DESTINATION_PRIVACYSHIELD_PRIVACY_NOTICE'), (6, 'DESTINATION_GLOBAL_PRIVACY_NOTICE'), (7, 'DESTINATION_GLOBAL_GDPR_PRIVACY_NOTICE')], default=6, help_text='SERVICE_DESTINATION_REGION_HELPTEXT', verbose_name='LABEL_DESTINATION_REGION'),
        ),
    ]
