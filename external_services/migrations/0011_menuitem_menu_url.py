# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from urllib.parse import urljoin, urlsplit
from django.db import migrations, models

def forwards(apps, schema_editor):
    MenuItem = apps.get_model('external_services', 'MenuItem')
    items = (MenuItem.objects.all()
             .exclude(service=None)
             .exclude(menu_url=None)
             .exclude(menu_url=''))
    errors = []
    for item in items:
        uri1 = urlsplit(item.menu_url)
        uri2 = urlsplit(item.service.url)
        if uri1.netloc and uri1.netloc != uri2.netloc:
            errors.append(item)
    if errors:
        print()
        msg = ['Database is in inconsistent state.']
        for item in errors:
            msg.append("  MenuItem(pk=%s): %s <> %s" % (item.pk, item.menu_url, item.service.url))
        msg.append("For above menuitems, domain in MenuItem.menu_url doesn't match domain in MenuItem.service.url.")
        msg.append("Database is in inconsistent state. Manual fixing is required.")
        raise RuntimeError('\n'.join(msg))
    for item in items:
        uri = urlsplit(item.menu_url)
        url = uri._replace(scheme='', netloc='').geturl()
        item.menu_url = url
        item.save(update_fields=['menu_url'])

def backwards(apps, schema_editor):
    MenuItem = apps.get_model('external_services', 'MenuItem')
    for item in MenuItem.objects.all():
        item.menu_url = urljoin(item.service.url, item.menu_url)
        item.save(update_fields=['menu_url'])

class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('external_services', '0010_auto_20180918_1916'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
