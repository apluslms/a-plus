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
        logger.debug("Invalidating cached data for %s", cache_key)
        cache.delete(cache_key)

    def __init__(self, *models, modifiers=[]):
        cache_key = self.__class__._key(*models, modifiers=modifiers)
        data = cache.get(cache_key)

        if self._needs_generation(data):
            # invalidate old value
            if data is not None:
                cache.delete(cache_key)

            # generate
            self.dirty = False
            gen_start_ts = timezone.now()
            logger.debug("Generating cached data for %s with ts %s", cache_key, gen_start_ts)
            data = self._generate_data(*models, data=data)

            # if another process invalidated the cache during the time consuming
            # generation cache.add() doesn't do anything
            cache_updated = cache.add(cache_key, data, None)
            if cache_updated:
                logger.debug("Set newly generated data for %s with ts %s", cache_key, gen_start_ts)
            else:
                logger.debug("Discarded generated data for %s with ts %s", cache_key, gen_start_ts)

                # Check that the data exists in the cache. If it doesn't then our update most likely failed
                if cache.get(cache_key) is None:
                    logger.error("Cache update failed for %s", cache_key)

        # in either case set the data
        self.data = data

    def _needs_generation(self, data):
        return data is None

    def _generate_data(self, *models, data=None):
        raise NotImplementedError("Subclass of CachedAbstract needs to implement _generate_data")
