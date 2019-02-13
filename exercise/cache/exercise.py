import time
from django.conf import settings
from django.db.models.signals import post_save, post_delete

from lib.cache import CachedAbstract
from lib.remote_page import RemotePageNotModified
from ..protocol.aplus import load_exercise_page


class ExerciseCache(CachedAbstract):
    """ Exercise HTML content """
    KEY_PREFIX = "exercise"

    def __init__(self, exercise, language, request, students, url_name):
        self.exercise = exercise
        self.load_args = [language, request, students, url_name]
        super().__init__(exercise, modifiers=[language])

    def _needs_generation(self, data):
        expires = data['expires'] if data else None
        return not expires or time.time() > expires

    def _generate_data(self, exercise, data=None):
        try:
            page = exercise.load_page(
                *self.load_args,
                last_modified=data['last_modified'] if data else None
            )
            return {
                'head': page.head,
                'content': page.content,
                'last_modified': page.last_modified,
                'expires': page.expires if page.is_loaded else 0,
            }
        except RemotePageNotModified as e:
            if e.expires:
                data['expires'] = e.expires
            return data

    def head(self):
        return self.data['head']

    def content(self):
        return self.data['content']


def invalidate_instance(instance):
    for module in instance.course_modules.all():
        for exercise in module.learning_objects.all():
            for language,_ in settings.LANGUAGES:
                ExerciseCache.invalidate(exercise, modifiers=[language])
