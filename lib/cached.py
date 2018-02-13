from django.core.cache import cache
from django.utils import timezone
import logging


logger = logging.getLogger("cached")


class CachedAbstract(object):
    KEY_PREFIX = 'abstract'

    @classmethod
    def _key(cls, *models, modifiers):
        return "{}:{}".format(cls.KEY_PREFIX, ",".join(
            [str(m.pk if hasattr(m, 'pk') else 0) for m in models]
            + modifiers
        ))

    @classmethod
    def invalidate(cls, *models, modifiers=[]):
        cache_key = cls._key(*models, modifiers=modifiers)
        ts = timezone.now()
        logger.debug("Invalidating cached data for {} with ts {}".format(cache_key, str(ts)))
        invalidated = {
                "invalidation_ts": ts
                }
        # overwrite the current cache with this invalidation timestamp
        # this could be basically anything but ts is nice if debugging needs to be done
        cache.set(cache_key, invalidated, 60*60)

    def __init__(self, *models, modifiers=[]):
        cache_key = self.__class__._key(*models, modifiers=modifiers)
        data = cache.get(cache_key)

        # if invalidation_ts exists in the returned data, lets
        # pass none to _needs_generation since its implementation
        # depends on it. from _needs_generation's point of fiew
        # nothing has changed
        if data is not None and "invalidation_ts" in data:
            data = None

        if self._needs_generation(data):

            gen_start_ts = timezone.now()
            logger.debug("Generating cached data for {} with ts {}".format(cache_key, str(gen_start_ts)))
            self.dirty = False

            # before cache regeneration delete the entry
            cache.delete(cache_key)
            data = self._generate_data(*models, data=data)

            # if another process invalidated the cache during the time consuming
            # generation cache.add() doesn't do anything
            cache_updated = cache.add(cache_key, data, None)
            if cache_updated:
                logger.debug("Set newly generated data for {} with ts {}".format(cache_key, str(gen_start_ts)))
            else:
                logger.debug("Discarded generated data for {} with ts {}".format(cache_key, str(gen_start_ts)))

        # in either case return the data
        self.data = data

    def _needs_generation(self, data):
        return data is None

    def _generate_data(self, *models, data=None):
        # Insert the time consuming data generation.
        print("Failed by using CachedAbstract directly.")
        assert False
