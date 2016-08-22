from django.core.cache import cache


class CachedAbstract(object):
    KEY_PREFIX = 'abstract'

    @classmethod
    def _key(cls, *models):
        return '{}:{}'.format(cls.KEY_PREFIX, ','.join([str(m.pk) for m in models]))

    @classmethod
    def invalidate(cls, *models):
        cache.delete(cls._key(*models))

    def __init__(self, *models):
        cache_key = self.__class__._key(*models)
        data = cache.get(cache_key)
        if data is None:
            data = self._generate_data(*models)
            cache.set(cache_key, data, None)
        self.data = data

    def _generate_data(self, *models):
        # Insert the time consuming data generation.
        print("Failed by using CachedAbstract directly.")
        assert False
