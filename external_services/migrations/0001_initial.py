# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inheritance', '0001_initial'),
        ('course', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LinkService',
            fields=[
                ('modelwithinheritance_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='inheritance.ModelWithInheritance')),
                ('url', models.CharField(help_text=b'The service URL', max_length=256)),
                ('menu_label', models.CharField(help_text=b'A default label to show in the course menu.', max_length=32)),
                ('menu_icon_class', models.CharField(default=b'icon-globe', help_text=b'A default menu icon style name, see http://getbootstrap.com/components/#glyphicons-glyphs', max_length=32)),
                ('enabled', models.BooleanField(default=True, help_text=b'If not enabled, the service is disabled for all course instances.')),
            ],
            options={
                'ordering': ['menu_label'],
            },
            bases=('inheritance.modelwithinheritance',),
        ),
        migrations.CreateModel(
            name='LTIService',
            fields=[
                ('linkservice_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='external_services.LinkService')),
                ('consumer_key', models.CharField(help_text=b'The consumer key provided by the LTI service.', max_length=128)),
                ('consumer_secret', models.CharField(help_text=b'The consumer secret provided by the LTI service.', max_length=128)),
            ],
            options={
            },
            bases=('external_services.linkservice',),
        ),
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('menu_label', models.CharField(help_text=b'Overrides service default label shown in the course menu.', max_length=32, null=True, blank=True)),
                ('menu_icon_class', models.CharField(help_text=b'Overrides service default menu icon style, e.g. icon-star see http://getbootstrap.com/components/#glyphicons-glyphs', max_length=32, null=True, blank=True)),
                ('menu_weight', models.IntegerField(default=0, help_text=b'Heavier menu entries are placed after lighter ones.')),
                ('enabled', models.BooleanField(default=True)),
                ('course_instance', models.ForeignKey(related_name='ext_services', to='course.CourseInstance', help_text=b'A course instance where the service is used.')),
                ('service', models.ForeignKey(to='external_services.LinkService')),
            ],
            options={
                'ordering': ['course_instance', 'menu_weight', 'menu_label'],
            },
            bases=(models.Model,),
        ),
    ]
