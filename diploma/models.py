import hashlib, time
from django.db import models

from course.models import CourseInstance, CourseModule
from exercise.models import BaseExercise
from lib.fields import JSONField
from lib.models import UrlMixin
from userprofile.models import UserProfile


def build_upload_dir(instance, filename):
    return "diploma/{:d}_{}".format(instance.id, safe_file_name(filename))


class CourseDiplomaDesign(models.Model):
    course = models.OneToOneField(CourseInstance, on_delete=models.SET_NULL, null=True)
    logo = models.ImageField(blank=True, null=True, upload_to=build_upload_dir)
    title = models.TextField()
    body = models.TextField()
    date = models.CharField(max_length=256)
    signature_name = models.CharField(max_length=256)
    signature_title = models.CharField(max_length=256)
    small_print = models.TextField()
    point_limits = JSONField(blank=True, help_text=(
        "A list of length 5 where each element is the required points for n:th grade."
        "The element can be a list of 2-tuples [[difficulty_level_a, points],[difficulty_level_b, points]]."
    ))
    pad_points = models.BooleanField(default=False, help_text=(
        "If difficulty levels are used the lower level can be padded with higher level points."
    ))
    exercises_to_pass = models.ManyToManyField(BaseExercise)
    modules_to_pass = models.ManyToManyField(CourseModule)


class StudentDiploma(UrlMixin, models.Model):
    design = models.ForeignKey(CourseDiplomaDesign, on_delete=models.CASCADE)
    profile = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now=True)
    hashkey = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    grade = models.PositiveIntegerField(default=0)

    def generate_hashkey(self):
        key = None
        while not key or self.objects.filter(hashkey=key).count() > 0:
            m = hashlib.md5()
            m.update("{:d}-{:d}-{:f}".format(
                self.design.id,
                self.profile.id,
                time.time()
            ))
            key = m.hexdigest()
        self.hashkey = key

    ABSOLUTE_URL_NAME = 'diploma-view'

    def get_url_kwargs(self):
        return { 'diploma_hash': self.hash }
