# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
        ('inheritance', '0001_initial'),
        ('oauth_provider', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='BasePlugin',
            fields=[
                ('modelwithinheritance_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='inheritance.ModelWithInheritance')),
                ('container_pk', models.TextField(verbose_name='object ID')),
                ('title', models.CharField(max_length=64)),
                ('views', models.CharField(max_length=255, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('inheritance.modelwithinheritance',),
        ),
        migrations.CreateModel(
            name='BaseTab',
            fields=[
                ('modelwithinheritance_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='inheritance.ModelWithInheritance')),
                ('container_pk', models.TextField(verbose_name='object ID')),
                ('label', models.CharField(max_length=12)),
                ('title', models.CharField(max_length=64)),
                ('order', models.IntegerField(default=100)),
                ('opening_method', models.CharField(max_length=32, blank=True)),
            ],
            options={
                'ordering': ['order', 'id'],
            },
            bases=('inheritance.modelwithinheritance',),
        ),
        migrations.CreateModel(
            name='EmbeddedTab',
            fields=[
                ('basetab_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='apps.BaseTab')),
                ('content_url', models.URLField(max_length=128)),
                ('element_id', models.CharField(max_length=32, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('apps.basetab',),
        ),
        migrations.CreateModel(
            name='ExternalIFramePlugin',
            fields=[
                ('baseplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='apps.BasePlugin')),
                ('service_url', models.URLField(max_length=255)),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
            bases=('apps.baseplugin',),
        ),
        migrations.CreateModel(
            name='ExternalIFrameTab',
            fields=[
                ('basetab_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='apps.BaseTab')),
                ('content_url', models.URLField(max_length=255)),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
            bases=('apps.basetab',),
        ),
        migrations.CreateModel(
            name='HTMLPlugin',
            fields=[
                ('baseplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='apps.BasePlugin')),
                ('content', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=('apps.baseplugin',),
        ),
        migrations.CreateModel(
            name='HTMLTab',
            fields=[
                ('basetab_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='apps.BaseTab')),
                ('content', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=('apps.basetab',),
        ),
        migrations.CreateModel(
            name='RSSPlugin',
            fields=[
                ('baseplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='apps.BasePlugin')),
                ('feed_url', models.URLField(max_length=256)),
            ],
            options={
                'abstract': False,
            },
            bases=('apps.baseplugin',),
        ),
        migrations.AddField(
            model_name='basetab',
            name='container_type',
            field=models.ForeignKey(to='contenttypes.ContentType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='basetab',
            name='oauth_consumer',
            field=models.ForeignKey(blank=True, to='oauth_provider.Consumer', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='baseplugin',
            name='container_type',
            field=models.ForeignKey(to='contenttypes.ContentType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='baseplugin',
            name='oauth_consumer',
            field=models.ForeignKey(blank=True, to='oauth_provider.Consumer', null=True),
            preserve_default=True,
        ),
    ]
