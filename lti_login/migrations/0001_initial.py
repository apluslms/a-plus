from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    
 
    def forwards(self, orm):
        
        db.create_table('lti_login_ltiservice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('lti_url', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('consumer_key', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('consumer_secret', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('menu_label', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('menu_icon_class', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('lti_login', ['LTIService'])
        
        db.create_table('lti_login_ltimenuitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'menu_items', to=orm['lti_login.LTIService'])),
            ('course_instance', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'lti_services', to=orm['course.CourseInstance'])),
            ('menu_label', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('menu_icon_class', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('menu_weight', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('lti_login', ['LTIMenuItem'])


    def backwards(self, orm):
        
        db.delete_table('lti_login_ltiservice')
        db.delete_table('lti_login_ltimenuitem')
    

    models = {
        
        'lti_login.ltiservice': {
            'Meta': { 'object_name': 'LTIService', 'ordering': "['menu_label']"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lti_url': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'consumer_key': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'consumer_secret': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'menu_label': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'menu_icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
        },
        'lti_login.ltimenuitem': {
            'Meta': { 'object_name': 'LTIMenuItem', 'ordering': "['course_instance', 'menu_weight', 'menu_label']"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'menu_items'", 'to': "orm['lti_login.LTIService']"}),
            'course_instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'lti_services'", 'to': "orm['course.CourseInstance']"}),
            'menu_label': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'menu_icon_class': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'menu_weight': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
        },
        
        'course.course': {
            'Meta': {'object_name': 'Course'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'teachers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'teaching_courses'", 'blank': 'True', 'to': "orm['userprofile.UserProfile']"}),
            'url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '16'})
        },
        'course.courseinstance': {
            'Meta': {'unique_together': "(('course', 'url'),)", 'object_name': 'CourseInstance'},
            'assistants': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'assisting_courses'", 'blank': 'True', 'to': "orm['userprofile.UserProfile']"}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'instances'", 'to': "orm['course.Course']"}),
            'ending_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'starting_time': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'website': ('django.db.models.fields.URLField', [], {'max_length': '30', 'blank': 'True'})
        },
        
        'userprofile.userprofile': {
            'Meta': {'ordering': "['id']", 'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lang': ('django.db.models.fields.CharField', [], {'default': "'en_US'", 'max_length': '5'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '25', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
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
    }
    

    complete_apps = ['lti_login']
