# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.utils import timezone


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BaseTab'
        db.create_table('apps_basetab', (
            ('modelwithinheritance_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['inheritance.ModelWithInheritance'], unique=True, primary_key=True)),
            ('container_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('container_pk', self.gf('django.db.models.fields.TextField')()),
            ('oauth_consumer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oauth_provider.Consumer'], null=True, blank=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=100)),
            ('opening_method', self.gf('django.db.models.fields.CharField')(max_length=32, blank=True)),
        ))
        db.send_create_signal('apps', ['BaseTab'])

        # Adding model 'HTMLTab'
        db.create_table('apps_htmltab', (
            ('basetab_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['apps.BaseTab'], unique=True, primary_key=True)),
            ('content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('apps', ['HTMLTab'])

        # Adding model 'ExternalTab'
        db.create_table('apps_externaltab', (
            ('basetab_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['apps.BaseTab'], unique=True, primary_key=True)),
            ('content_url', self.gf('django.db.models.fields.URLField')(max_length=128)),
        ))
        db.send_create_signal('apps', ['ExternalTab'])

        # Adding model 'EmbeddedTab'
        db.create_table('apps_embeddedtab', (
            ('basetab_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['apps.BaseTab'], unique=True, primary_key=True)),
            ('content_url', self.gf('django.db.models.fields.URLField')(max_length=128)),
            ('element_id', self.gf('django.db.models.fields.CharField')(max_length=32, blank=True)),
        ))
        db.send_create_signal('apps', ['EmbeddedTab'])

        # Adding model 'BasePlugin'
        db.create_table('apps_baseplugin', (
            ('modelwithinheritance_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['inheritance.ModelWithInheritance'], unique=True, primary_key=True)),
            ('container_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('container_pk', self.gf('django.db.models.fields.TextField')()),
            ('oauth_consumer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['oauth_provider.Consumer'], null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('apps', ['BasePlugin'])

        # Adding model 'RSSPlugin'
        db.create_table('apps_rssplugin', (
            ('baseplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['apps.BasePlugin'], unique=True, primary_key=True)),
            ('feed_url', self.gf('django.db.models.fields.URLField')(max_length=256)),
        ))
        db.send_create_signal('apps', ['RSSPlugin'])

        # Adding model 'IFramePlugin'
        db.create_table('apps_iframeplugin', (
            ('baseplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['apps.BasePlugin'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('apps', ['IFramePlugin'])

        # Adding model 'EmbeddedPlugin'
        db.create_table('apps_embeddedplugin', (
            ('baseplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['apps.BasePlugin'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('apps', ['EmbeddedPlugin'])

        # Adding model 'HTMLPlugin'
        db.create_table('apps_htmlplugin', (
            ('baseplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['apps.BasePlugin'], unique=True, primary_key=True)),
            ('content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('apps', ['HTMLPlugin'])

        # Adding model 'ChatPlugin'
        db.create_table('apps_chatplugin', (
            ('baseplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['apps.BasePlugin'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('apps', ['ChatPlugin'])


    def backwards(self, orm):
        # Deleting model 'BaseTab'
        db.delete_table('apps_basetab')

        # Deleting model 'HTMLTab'
        db.delete_table('apps_htmltab')

        # Deleting model 'ExternalTab'
        db.delete_table('apps_externaltab')

        # Deleting model 'EmbeddedTab'
        db.delete_table('apps_embeddedtab')

        # Deleting model 'BasePlugin'
        db.delete_table('apps_baseplugin')

        # Deleting model 'RSSPlugin'
        db.delete_table('apps_rssplugin')

        # Deleting model 'IFramePlugin'
        db.delete_table('apps_iframeplugin')

        # Deleting model 'EmbeddedPlugin'
        db.delete_table('apps_embeddedplugin')

        # Deleting model 'HTMLPlugin'
        db.delete_table('apps_htmlplugin')

        # Deleting model 'ChatPlugin'
        db.delete_table('apps_chatplugin')


    models = {
        'apps.baseplugin': {
            'Meta': {'object_name': 'BasePlugin'},
            'container_pk': ('django.db.models.fields.TextField', [], {}),
            'container_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'modelwithinheritance_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['inheritance.ModelWithInheritance']", 'unique': 'True', 'primary_key': 'True'}),
            'oauth_consumer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oauth_provider.Consumer']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'apps.basetab': {
            'Meta': {'ordering': "['order', 'id']", 'object_name': 'BaseTab'},
            'container_pk': ('django.db.models.fields.TextField', [], {}),
            'container_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'modelwithinheritance_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['inheritance.ModelWithInheritance']", 'unique': 'True', 'primary_key': 'True'}),
            'oauth_consumer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oauth_provider.Consumer']", 'null': 'True', 'blank': 'True'}),
            'opening_method': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '100'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'apps.chatplugin': {
            'Meta': {'object_name': 'ChatPlugin', '_ormbases': ['apps.BasePlugin']},
            'baseplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['apps.BasePlugin']", 'unique': 'True', 'primary_key': 'True'})
        },
        'apps.embeddedplugin': {
            'Meta': {'object_name': 'EmbeddedPlugin', '_ormbases': ['apps.BasePlugin']},
            'baseplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['apps.BasePlugin']", 'unique': 'True', 'primary_key': 'True'})
        },
        'apps.embeddedtab': {
            'Meta': {'ordering': "['order', 'id']", 'object_name': 'EmbeddedTab', '_ormbases': ['apps.BaseTab']},
            'basetab_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['apps.BaseTab']", 'unique': 'True', 'primary_key': 'True'}),
            'content_url': ('django.db.models.fields.URLField', [], {'max_length': '128'}),
            'element_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'})
        },
        'apps.externaltab': {
            'Meta': {'ordering': "['order', 'id']", 'object_name': 'ExternalTab', '_ormbases': ['apps.BaseTab']},
            'basetab_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['apps.BaseTab']", 'unique': 'True', 'primary_key': 'True'}),
            'content_url': ('django.db.models.fields.URLField', [], {'max_length': '128'})
        },
        'apps.htmlplugin': {
            'Meta': {'object_name': 'HTMLPlugin', '_ormbases': ['apps.BasePlugin']},
            'baseplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['apps.BasePlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {})
        },
        'apps.htmltab': {
            'Meta': {'ordering': "['order', 'id']", 'object_name': 'HTMLTab', '_ormbases': ['apps.BaseTab']},
            'basetab_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['apps.BaseTab']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {})
        },
        'apps.iframeplugin': {
            'Meta': {'object_name': 'IFramePlugin', '_ormbases': ['apps.BasePlugin']},
            'baseplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['apps.BasePlugin']", 'unique': 'True', 'primary_key': 'True'})
        },
        'apps.rssplugin': {
            'Meta': {'object_name': 'RSSPlugin', '_ormbases': ['apps.BasePlugin']},
            'baseplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['apps.BasePlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '256'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'timezone.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'timezone.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'inheritance.modelwithinheritance': {
            'Meta': {'object_name': 'ModelWithInheritance'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'oauth_provider.consumer': {
            'Meta': {'object_name': 'Consumer'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['apps']
