# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.utils import timezone


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LinkService'
        db.create_table('external_services_linkservice', (
            ('modelwithinheritance_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['inheritance.ModelWithInheritance'], unique=True, primary_key=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('menu_label', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('menu_icon_class', self.gf('django.db.models.fields.CharField')(default='icon-globe', max_length=32)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('external_services', ['LinkService'])

        # Adding model 'LTIService'
        db.create_table('external_services_ltiservice', (
            ('linkservice_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['external_services.LinkService'], unique=True, primary_key=True)),
            ('consumer_key', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('consumer_secret', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('external_services', ['LTIService'])

        # Adding model 'MenuItem'
        db.create_table('external_services_menuitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['external_services.LinkService'])),
            ('course_instance', self.gf('django.db.models.fields.related.ForeignKey')(related_name='ext_services', to=orm['course.CourseInstance'])),
            ('menu_label', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('menu_icon_class', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('menu_weight', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('external_services', ['MenuItem'])


    def backwards(self, orm):
        # Deleting model 'LinkService'
        db.delete_table('external_services_linkservice')

        # Deleting model 'LTIService'
        db.delete_table('external_services_ltiservice')

        # Deleting model 'MenuItem'
        db.delete_table('external_services_menuitem')


    models = {
        'apps.baseplugin': {
            'Meta': {'object_name': 'BasePlugin'},
            'container_pk': ('django.db.models.fields.TextField', [], {}),
            'container_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'modelwithinheritance_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['inheritance.ModelWithInheritance']", 'unique': 'True', 'primary_key': 'True'}),
            'oauth_consumer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oauth_provider.Consumer']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'views': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
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
        'course.course': {
            'Meta': {'object_name': 'Course'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'teachers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'teaching_courses'", 'blank': 'True', 'to': "orm['userprofile.UserProfile']"}),
            'url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'course.courseinstance': {
            'Meta': {'unique_together': "(('course', 'url'),)", 'object_name': 'CourseInstance'},
            'assistants': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'assisting_courses'", 'blank': 'True', 'to': "orm['userprofile.UserProfile']"}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'instances'", 'to': "orm['course.Course']"}),
            'ending_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'starting_time': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'visible_to_students': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'max_length': '255', 'blank': 'True'})
        },
        'external_services.linkservice': {
            'Meta': {'ordering': "['menu_label']", 'object_name': 'LinkService', '_ormbases': ['inheritance.ModelWithInheritance']},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'menu_icon_class': ('django.db.models.fields.CharField', [], {'default': "'icon-globe'", 'max_length': '32'}),
            'menu_label': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modelwithinheritance_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['inheritance.ModelWithInheritance']", 'unique': 'True', 'primary_key': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'external_services.ltiservice': {
            'Meta': {'ordering': "['menu_label']", 'object_name': 'LTIService', '_ormbases': ['external_services.LinkService']},
            'consumer_key': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'consumer_secret': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'linkservice_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['external_services.LinkService']", 'unique': 'True', 'primary_key': 'True'})
        },
        'external_services.menuitem': {
            'Meta': {'ordering': "['course_instance', 'menu_weight', 'menu_label']", 'object_name': 'MenuItem'},
            'course_instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ext_services'", 'to': "orm['course.CourseInstance']"}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'menu_icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'menu_label': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'menu_weight': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['external_services.LinkService']"})
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
        },
        'userprofile.userprofile': {
            'Meta': {'ordering': "['id']", 'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lang': ('django.db.models.fields.CharField', [], {'default': "'en_US'", 'max_length': '5'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '25', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['external_services']
