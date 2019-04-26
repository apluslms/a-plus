# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.utils import timezone
import datetime
import exercise.submission_models
import lib.helpers
import exercise.exercise_models
import lib.fields


class Migration(migrations.Migration):

    dependencies = [
        ('inheritance', '0001_initial'),
        ('userprofile', '0001_initial'),
        ('course', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseModule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('points_to_pass', models.PositiveIntegerField(default=0)),
                ('introduction', models.TextField(blank=True)),
                ('opening_time', models.DateTimeField(default=timezone.now)),
                ('closing_time', models.DateTimeField(default=timezone.now)),
                ('late_submissions_allowed', models.BooleanField(default=False)),
                ('late_submission_deadline', models.DateTimeField(default=timezone.now)),
                ('late_submission_penalty', lib.fields.PercentField(default=0.5, help_text='Multiplier of points to reduce, as decimal. 0.1 = 10%')),
                ('course_instance', models.ForeignKey(related_name='course_modules', to='course.CourseInstance', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['closing_time', 'id'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DeadlineRuleDeviation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('extra_minutes', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LearningObject',
            fields=[
                ('modelwithinheritance_ptr', models.OneToOneField(
                    to='inheritance.ModelWithInheritance', on_delete=models.CASCADE,
                    parent_link=True, auto_created=True, primary_key=True, serialize=False)),
                ('order', models.IntegerField(default=0)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('instructions', models.TextField(blank=True)),
                ('service_url', models.URLField(blank=True)),
            ],
            options={
            },
            bases=('inheritance.modelwithinheritance',),
        ),
        migrations.CreateModel(
            name='BaseExercise',
            fields=[
                ('learningobject_ptr', models.OneToOneField(
                    to='exercise.LearningObject', on_delete=models.CASCADE,
                    parent_link=True, auto_created=True, primary_key=True, serialize=False)),
                ('allow_assistant_grading', models.BooleanField(default=False)),
                ('min_group_size', models.PositiveIntegerField(default=1)),
                ('max_group_size', models.PositiveIntegerField(default=1)),
                ('max_submissions', models.PositiveIntegerField(default=10)),
                ('max_points', models.PositiveIntegerField(default=100)),
                ('points_to_pass', models.PositiveIntegerField(default=40)),
            ],
            options={
                'ordering': ['course_module__closing_time', 'course_module', 'order', 'id'],
            },
            bases=('exercise.learningobject',),
        ),
        migrations.CreateModel(
            name='ExerciseWithAttachment',
            fields=[
                ('baseexercise_ptr', models.OneToOneField(
                    to='exercise.BaseExercise', on_delete=models.CASCADE,
                    parent_link=True, auto_created=True, primary_key=True, serialize=False)),
                ('files_to_submit', models.CharField(help_text='File names that user should submit, use pipe character to separate files', max_length=200, blank=True)),
                ('attachment', models.FileField(upload_to=exercise.exercise_models.build_upload_dir)),
            ],
            options={
                'verbose_name_plural': 'exercises with attachment',
            },
            bases=('exercise.baseexercise',),
        ),
        migrations.CreateModel(
            name='AsynchronousExercise',
            fields=[
                ('baseexercise_ptr', models.OneToOneField(
                    to='exercise.BaseExercise', on_delete=models.CASCADE,
                    parent_link=True, auto_created=True, primary_key=True, serialize=False)),
            ],
            options={
            },
            bases=('exercise.baseexercise',),
        ),
        migrations.CreateModel(
            name='LearningObjectCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=35)),
                ('description', models.TextField(blank=True)),
                ('points_to_pass', models.PositiveIntegerField(default=0)),
                ('course_instance', models.ForeignKey(related_name='categories', to='course.CourseInstance', on_delete=models.CASCADE)),
                ('hidden_to', models.ManyToManyField(related_name='hidden_categories', null=True, to='userprofile.UserProfile', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MaxSubmissionsRuleDeviation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('extra_submissions', models.IntegerField()),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StaticExercise',
            fields=[
                ('baseexercise_ptr', models.OneToOneField(
                    to='exercise.BaseExercise', on_delete=models.CASCADE,
                    parent_link=True, auto_created=True, primary_key=True, serialize=False)),
                ('exercise_page_content', models.TextField()),
                ('submission_page_content', models.TextField()),
            ],
            options={
            },
            bases=('exercise.baseexercise',),
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submission_time', models.DateTimeField(auto_now_add=True)),
                ('hash', models.CharField(default=lib.helpers.get_random_string, max_length=32)),
                ('feedback', models.TextField(blank=True)),
                ('assistant_feedback', models.TextField(blank=True)),
                ('status', models.CharField(default=b'initialized', max_length=32, choices=[(b'initialized', 'Initialized'), (b'waiting', 'Waiting'), (b'ready', 'Ready'), (b'error', 'Error')])),
                ('grade', models.IntegerField(default=0)),
                ('grading_time', models.DateTimeField(null=True, blank=True)),
                ('service_points', models.IntegerField(default=0)),
                ('service_max_points', models.IntegerField(default=0)),
                ('submission_data', lib.fields.JSONField(blank=True)),
                ('grading_data', lib.fields.JSONField(blank=True)),
            ],
            options={
                'ordering': ['-submission_time'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubmittedFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('param_name', models.CharField(max_length=128)),
                ('file_object', models.FileField(max_length=255, upload_to=exercise.submission_models.build_upload_dir)),
                ('submission', models.ForeignKey(related_name='files', to='exercise.Submission', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SynchronousExercise',
            fields=[
                ('baseexercise_ptr', models.OneToOneField(
                    to='exercise.BaseExercise', on_delete=models.CASCADE,
                    parent_link=True, auto_created=True, primary_key=True, serialize=False)),
            ],
            options={
            },
            bases=('exercise.baseexercise',),
        ),
        migrations.AddField(
            model_name='submission',
            name='exercise',
            field=models.ForeignKey(related_name='submissions', to='exercise.BaseExercise', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submission',
            name='grader',
            field=models.ForeignKey(related_name='graded_submissions', blank=True, to='userprofile.UserProfile', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submission',
            name='submitters',
            field=models.ManyToManyField(related_name='submissions', to='userprofile.UserProfile'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='maxsubmissionsruledeviation',
            name='exercise',
            field=models.ForeignKey(related_name='maxsubmissionsruledeviations', to='exercise.BaseExercise', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='maxsubmissionsruledeviation',
            name='submitter',
            field=models.ForeignKey(to='userprofile.UserProfile', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='maxsubmissionsruledeviation',
            unique_together=set([('exercise', 'submitter')]),
        ),
        migrations.AlterUniqueTogether(
            name='learningobjectcategory',
            unique_together=set([('name', 'course_instance')]),
        ),
        migrations.AddField(
            model_name='learningobject',
            name='category',
            field=models.ForeignKey(related_name='learning_objects', to='exercise.LearningObjectCategory', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='learningobject',
            name='course_module',
            field=models.ForeignKey(related_name='learning_objects', to='exercise.CourseModule', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='deadlineruledeviation',
            name='exercise',
            field=models.ForeignKey(related_name='deadlineruledeviations', to='exercise.BaseExercise', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='deadlineruledeviation',
            name='submitter',
            field=models.ForeignKey(to='userprofile.UserProfile', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='deadlineruledeviation',
            unique_together=set([('exercise', 'submitter')]),
        ),
    ]
