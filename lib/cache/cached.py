from datetime import datetime
from django.core.cache import cache
from time import time
import logging


logger = logging.getLogger('aplus.cached')


class CachedAbstract:
    KEY_PREFIX = 'abstract'

    @classmethod
    def _key(cls, *models, modifiers):
        keys = [str(m if isinstance(m, int) else getattr(m, 'pk', None))
                for m in models]
        keys.extend(modifiers)
        return "%s:%s" % (cls.KEY_PREFIX, ','.join(keys))

    @classmethod
    def invalidate(cls, *models, modifiers=[]): # pylint: disable=dangerous-default-value
        cache_key = cls._key(*models, modifiers=modifiers)
        logger.debug("Invalidating cached data for %s", cache_key)
        # The cache is invalid, if the time field is None
        # The invalidation time is stored in the data field for debug messages
        # Keep this value in the cache for an hour, so it will be removed from
        # the memory at some point, but not before all generations have finished.
        cache.set(cache_key, (None, time()), 60*60)

    def __init__(self, *models, modifiers=[]): # pylint: disable=dangerous-default-value
        self.__models = models
        self.__cache_key = self.__class__._key(*models, modifiers=modifiers)
        self.data = self.__get_data()

    def __get_data(self):
        cache_key = self.__cache_key
        cache_name = "%s[%s]" % (self.__class__.__name__, cache_key)

        # Retrieve currently cached data
        raw = cache.get(cache_key)
        updated, data = raw if isinstance(raw, tuple) and len(raw) == 2 else (None, None)

        # Cache is invalidated, if updated is None
        if updated is None:
            data = None

        # Use the cached data, if it doesn't require regeneration
        # TODO: updated should be passed to _needs_generation
        if not self._needs_generation(data):
            return data

        # If the cache contains invalid value, clear it
        if raw is not None:
            cache.delete(cache_key)

        # Generate a new data
        self.dirty = False
        gen_start = time()
        gen_start_dt = str(datetime.fromtimestamp(gen_start))
        logger.debug("Generating cached data for %s with ts %s", cache_name, gen_start_dt)
        data = self._generate_data(*self.__models, data=data)

        # If another process invalidated the cache or generated a newer
        # value for it during the generation time, then cache.add()
        # returns False and keeps the current value in the cache
        cache_updated = cache.add(cache_key, (gen_start, data), None)
        if cache_updated:
            logger.debug("Set newly generated data for %s with ts %s", cache_name, gen_start_dt)
            # The generated value should be in the cache now
            return data

        current = cache.get(cache_key)
        if current is None:
            # The data was cleared before generation, but currently it is None,
            # thus cache wasn't invalidated, so the data was probably too big.
            # Best we can do is to log error and return the data
            logger.error("Failed to store a value to the cache %s. It might be too big!", cache_name)
            return data

        # Someone invalidated or updated the value in the cache before we completed
        curr_updated, curr_data = current if isinstance(current, tuple) and len(current) == 2 else (None, None)
        if curr_updated is None:
            # Update time is None, so data was invalidated.
            # New value is not stored in the cache, but returned
            try:
                curr_dt = datetime.fromtimestamp(curr_data) if curr_data is not None else None
            except: # noqa: E722
                curr_dt = repr(curr_data)
            logger.debug(
                "Cache %s was discarded at %s, before generation of a new data with ts %s was completed.",
                cache_name,
                curr_dt,
                gen_start_dt
            )
        elif curr_updated > gen_start:
            # Cache was updated before we were ready, so use the newer value
            try:
                curr_dt = datetime.fromtimestamp(curr_updated)
            except: # noqa: E722
                curr_dt = curr_updated
            logger.debug(
                (
                    "Cache %s was updated at %s, before generation of a new data with ts %s was completed. "
                    "Using newer value from the cache."
                ),
                cache_name,
                curr_dt,
                gen_start_dt
            )
            data = curr_data
        else:
            # We have newer value, so force the cache to this new value
            try:
                curr_dt = datetime.fromtimestamp(curr_updated)
            except: # noqa: E722
                curr_dt = curr_updated
            logger.debug(
                (
                    "Cache %s was updated at %s, before generation of a new data with ts %s was completed. "
                    "Updating the cache with our newer value!"
                ),
                cache_name,
                curr_dt,
                gen_start_dt
            )
            cache.set(cache_key, (gen_start, data), None)
            # NOTE: there is a chance that the cache was invalidated between
            # get and this set. To fix that, we would require operation
            # check-and-set (CAS), which is not supported by Django
        return data

    def _needs_generation(self, data):
        return data is None

    def _generate_data(self, *models, data=None):
        raise NotImplementedError("Subclass of CachedAbstract needs to implement _generate_data")
