from django.core.cache import cache

from .abstract import CachedAbstract


class CachedPoints(CachedAbstract):
    KEY_PREFIX = 'points'

    def __init__(self, course_instance, user):
        self.instance = course_instance
        self.user = user
        super().__init__(course_instance, user)

    def _generate_data(self, instance, user):

        return {}
