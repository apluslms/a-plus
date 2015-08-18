# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.utils import timezone


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CourseModule'
        db.create_table('exercise_coursemodule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('points_to_pass', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('introduction', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('course_instance', self.gf('django.db.models.fields.related.ForeignKey')(related_name='course_modules', to=orm['course.CourseInstance'])),
            ('opening_time', self.gf('django.db.models.fields.DateTimeField')(default=timezone.now)),
            ('closing_time', self.gf('django.db.models.fields.DateTimeField')(default=timezone.now)),
            ('late_submissions_allowed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('late_submission_deadline', self.gf('django.db.models.fields.DateTimeField')(default=timezone.now)),
            ('late_submission_penalty', self.gf('lib.fields.PercentField')(default=0.5)),
        ))
        db.send_create_signal('exercise', ['CourseModule'])

        # Adding model 'LearningObject'
        db.create_table('exercise_learningobject', (
            ('modelwithinheritance_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['inheritance.ModelWithInheritance'], unique=True, primary_key=True)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=35)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('instructions', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('service_url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('course_module', self.gf('django.db.models.fields.related.ForeignKey')(related_name='learning_objects', to=orm['exercise.CourseModule'])),
        ))
        db.send_create_signal('exercise', ['LearningObject'])

        # Adding model 'BaseExercise'
        db.create_table('exercise_baseexercise', (
            ('learningobject_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['exercise.LearningObject'], unique=True, primary_key=True)),
            ('allow_assistant_grading', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('min_group_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('max_group_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('max_submissions', self.gf('django.db.models.fields.PositiveIntegerField')(default=10)),
            ('max_points', self.gf('django.db.models.fields.PositiveIntegerField')(default=100)),
            ('points_to_pass', self.gf('django.db.models.fields.PositiveIntegerField')(default=40)),
        ))
        db.send_create_signal('exercise', ['BaseExercise'])

        # Adding model 'AsynchronousExercise'
        db.create_table('exercise_asynchronousexercise', (
            ('baseexercise_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['exercise.BaseExercise'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('exercise', ['AsynchronousExercise'])

        # Adding model 'SynchronousExercise'
        db.create_table('exercise_synchronousexercise', (
            ('baseexercise_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['exercise.BaseExercise'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('exercise', ['SynchronousExercise'])

        # Adding model 'StaticExercise'
        db.create_table('exercise_staticexercise', (
            ('baseexercise_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['exercise.BaseExercise'], unique=True, primary_key=True)),
            ('exercise_page_content', self.gf('django.db.models.fields.TextField')()),
            ('submission_page_content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('exercise', ['StaticExercise'])

        # Adding model 'Submission'
        db.create_table('exercise_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('hash', self.gf('django.db.models.fields.CharField')(default='ejEsOjnvsJziaGC5vWmbydNVCy9GmGzT', max_length=32)),
            ('exercise', self.gf('django.db.models.fields.related.ForeignKey')(related_name='submissions', to=orm['exercise.BaseExercise'])),
            ('grader', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='graded_submissions', null=True, to=orm['userprofile.UserProfile'])),
            ('feedback', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='initialized', max_length=32)),
            ('grade', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('grading_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('service_points', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('service_max_points', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('submission_data', self.gf('lib.fields.JSONField')(blank=True)),
            ('grading_data', self.gf('lib.fields.JSONField')(blank=True)),
        ))
        db.send_create_signal('exercise', ['Submission'])

        # Adding M2M table for field submitters on 'Submission'
        db.create_table('exercise_submission_submitters', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('submission', models.ForeignKey(orm['exercise.submission'], null=False)),
            ('userprofile', models.ForeignKey(orm['userprofile.userprofile'], null=False))
        ))
        db.create_unique('exercise_submission_submitters', ['submission_id', 'userprofile_id'])

        # Adding model 'SubmittedFile'
        db.create_table('exercise_submittedfile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(related_name='files', to=orm['exercise.Submission'])),
            ('param_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('file_object', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        ))
        db.send_create_signal('exercise', ['SubmittedFile'])


    def backwards(self, orm):
        # Deleting model 'CourseModule'
        db.delete_table('exercise_coursemodule')

        # Deleting model 'LearningObject'
        db.delete_table('exercise_learningobject')

        # Deleting model 'BaseExercise'
        db.delete_table('exercise_baseexercise')

        # Deleting model 'AsynchronousExercise'
        db.delete_table('exercise_asynchronousexercise')

        # Deleting model 'SynchronousExercise'
        db.delete_table('exercise_synchronousexercise')

        # Deleting model 'StaticExercise'
        db.delete_table('exercise_staticexercise')

        # Deleting model 'Submission'
        db.delete_table('exercise_submission')

        # Removing M2M table for field submitters on 'Submission'
        db.delete_table('exercise_submission_submitters')

        # Deleting model 'SubmittedFile'
        db.delete_table('exercise_submittedfile')


    models = {
        'apps.baseplugin': {
            'Meta': {'object_name': 'BasePlugin'},
            'container_pk': ('django.db.models.fields.TextField', [], {}),
            'container_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'modelwithinheritance_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['inheritance.ModelWithInheritance']", 'unique': 'True', 'primary_key': 'True'}),
            'oauth_consumer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['oauth_provider.Consumer']", 'null': 'True', 'blank': 'True'}),
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
            'website': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'exercise.asynchronousexercise': {
            'Meta': {'ordering': "['course_module__closing_time', 'course_module', 'order', 'id']", 'object_name': 'AsynchronousExercise', '_ormbases': ['exercise.BaseExercise']},
            'baseexercise_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['exercise.BaseExercise']", 'unique': 'True', 'primary_key': 'True'})
        },
        'exercise.baseexercise': {
            'Meta': {'ordering': "['course_module__closing_time', 'course_module', 'order', 'id']", 'object_name': 'BaseExercise', '_ormbases': ['exercise.LearningObject']},
            'allow_assistant_grading': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'learningobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['exercise.LearningObject']", 'unique': 'True', 'primary_key': 'True'}),
            'max_group_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'max_points': ('django.db.models.fields.PositiveIntegerField', [], {'default': '100'}),
            'max_submissions': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10'}),
            'min_group_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'points_to_pass': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40'})
        },
        'exercise.coursemodule': {
            'Meta': {'ordering': "['closing_time', 'id']", 'object_name': 'CourseModule'},
            'closing_time': ('django.db.models.fields.DateTimeField', [], {'default': 'timezone.now'}),
            'course_instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'course_modules'", 'to': "orm['course.CourseInstance']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'introduction': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'late_submission_deadline': ('django.db.models.fields.DateTimeField', [], {'default': 'timezone.now'}),
            'late_submission_penalty': ('lib.fields.PercentField', [], {'default': '0.5'}),
            'late_submissions_allowed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'opening_time': ('django.db.models.fields.DateTimeField', [], {'default': 'timezone.now'}),
            'points_to_pass': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'exercise.learningobject': {
            'Meta': {'object_name': 'LearningObject', '_ormbases': ['inheritance.ModelWithInheritance']},
            'course_module': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'learning_objects'", 'to': "orm['exercise.CourseModule']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'instructions': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modelwithinheritance_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['inheritance.ModelWithInheritance']", 'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'service_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'exercise.staticexercise': {
            'Meta': {'ordering': "['course_module__closing_time', 'course_module', 'order', 'id']", 'object_name': 'StaticExercise', '_ormbases': ['exercise.BaseExercise']},
            'baseexercise_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['exercise.BaseExercise']", 'unique': 'True', 'primary_key': 'True'}),
            'exercise_page_content': ('django.db.models.fields.TextField', [], {}),
            'submission_page_content': ('django.db.models.fields.TextField', [], {})
        },
        'exercise.submission': {
            'Meta': {'ordering': "['-submission_time']", 'object_name': 'Submission'},
            'exercise': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['exercise.BaseExercise']"}),
            'feedback': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'grade': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'grader': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'graded_submissions'", 'null': 'True', 'to': "orm['userprofile.UserProfile']"}),
            'grading_data': ('lib.fields.JSONField', [], {'blank': 'True'}),
            'grading_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "'dhVRPNpHtswcUaoUlkHeWNUe0nyXTIOo'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'service_max_points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'service_points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'initialized'", 'max_length': '32'}),
            'submission_data': ('lib.fields.JSONField', [], {'blank': 'True'}),
            'submission_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'submitters': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'submissions'", 'symmetrical': 'False', 'to': "orm['userprofile.UserProfile']"})
        },
        'exercise.submittedfile': {
            'Meta': {'object_name': 'SubmittedFile'},
            'file_object': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'param_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['exercise.Submission']"})
        },
        'exercise.synchronousexercise': {
            'Meta': {'ordering': "['course_module__closing_time', 'course_module', 'order', 'id']", 'object_name': 'SynchronousExercise', '_ormbases': ['exercise.BaseExercise']},
            'baseexercise_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['exercise.BaseExercise']", 'unique': 'True', 'primary_key': 'True'})
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

    complete_apps = ['exercise']
