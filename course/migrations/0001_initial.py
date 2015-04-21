# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('code', models.CharField(max_length=255)),
                ('url', models.CharField(help_text=b"Input an identifier for this course's URL.", unique=True, max_length=255, validators=[django.core.validators.RegexValidator(regex=b'^[\\w\\-\\.]*$')])),
                ('teachers', models.ManyToManyField(related_name='teaching_courses', to='userprofile.UserProfile', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CourseHook',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hook_url', models.URLField()),
                ('hook_type', models.CharField(default=b'post-grading', max_length=12, choices=[(b'post-grading', b'Post grading')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CourseInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('instance_name', models.CharField(max_length=255)),
                ('website', models.URLField(max_length=255, blank=True)),
                ('url', models.CharField(help_text=b'Input an URL identifier for this course.', max_length=255, validators=[django.core.validators.RegexValidator(regex=b'^[\\w\\-\\.]*$')])),
                ('starting_time', models.DateTimeField()),
                ('ending_time', models.DateTimeField()),
                ('visible_to_students', models.BooleanField(default=True)),
                ('assistants', models.ManyToManyField(related_name='assisting_courses', to='userprofile.UserProfile', blank=True)),
                ('course', models.ForeignKey(related_name='instances', to='course.Course')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='courseinstance',
            unique_together=set([('course', 'url')]),
        ),
        migrations.AddField(
            model_name='coursehook',
            name='course_instance',
            field=models.ForeignKey(related_name='course_hooks', to='course.CourseInstance'),
            preserve_default=True,
        ),
    ]
