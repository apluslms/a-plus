import logging
from time import time
from typing import Dict, Iterable, List, Optional, Tuple

from django.core.cache import cache
from django.db import connections, transaction

from ..request_globals import RequestGlobal

logger = logging.getLogger('aplus.cache')


def _get(key: str) -> Optional[Tuple[float, Optional[bytes]]]:
    return cache.get(key)


def _get_many(keys: Iterable[str]) -> Dict[str, Tuple[float, Optional[bytes]]]:
    return cache.get_many(keys) # type: ignore


def _set(key: str, item: Tuple[float, Optional[bytes]]) -> None:
    cache.set(key, item)


def _set_many(items: Dict[str, Tuple[float, Optional[bytes]]]) -> None:
    failed = cache.set_many(items)
    if failed:
        logger.warning("Failed to save the following in the cache: %s", "; ".join(failed))


def _savepoint_commit(original_func):
    def inner(sid):
        original_func(sid)
        CacheTransactionManager()._commit_memo()
    return inner


def _savepoint_rollback(original_func):
    def inner(sid):
        original_func(sid)
        CacheTransactionManager()._discard_memo()
    return inner


class CacheTransactionManager(RequestGlobal):
    """Handles cache interaction during database transactions. Cache operations
    are not committed to the cache if the transaction/savepoint is rolled back.

    Idea is that any invalidations/modifications made during a transaction only
    affect other requests if the transaction is committed. The invalidations
    and modifications do affect other actions taken during the transaction
    itself.
    """
    memos: List[Tuple[int, Dict[str, Tuple[float, Optional[bytes]]]]]
    commiting: Optional[int]

    def init(self):
        self.memos = []
        self.commiting = None
        conn = connections["default"]
        if "savepoint_commit" not in conn.__dict__:
            # logger.info("setting savepoint_commit")
            # Django doesn't support on_commit for savepoints, so we need to
            # monkey patch commit and rollback hooks into the actual methods
            conn.savepoint_commit = _savepoint_commit(conn.savepoint_commit)
            conn.savepoint_rollback =_savepoint_rollback(conn.savepoint_rollback)

    def get_many(self, keys: Iterable[str]) -> Dict[str, Tuple[float, Optional[bytes]]]:
        self._update_memos()
        memo = {}
        for _, m in self.memos:
            memo.update(m)

        items = _get_many(keys)
        if not memo:
            return items

        for k in set(keys).intersection(memo.keys()):
            v = memo[k]
            if v[0] < items.get(k, (0, None))[0]:
                # Something else updated the cache but they aren't aware of any
                # changes done during the transaction. Neither value can be trusted
                del items[k]
            else:
                items[k] = v

        return items

    def get(self, key: str) -> Optional[Tuple[float, Optional[bytes]]]:
        self._update_memos()
        item = _get(key)
        for _, m in reversed(self.memos):
            if key in m:
                v = m[key]
                if item is None:
                    return v

                if v[0] < item[0]:
                    # Something else updated the cache but they aren't aware of any
                    # changes done during the transaction. Neither value can be trusted
                    return None

                return v

        return item

    def set(self, key: str, item: Tuple[float, Optional[bytes]]) -> None:
        self._update_memos()
        if not self.memos:
            _set(key, item)
        else:
            self.memos[-1][1][key] = item
            self._set_on_commit()

    def set_many(self, items: Dict[str, Tuple[float, Optional[bytes]]]) -> None:
        self._update_memos()
        if not self.memos:
            _set_many(items)
        else:
            self.memos[-1][1].update(items)
            self._set_on_commit()

    def _get_memo_ids(self) -> List[int]:
        # These use Django's private API. They seem to be stable, and in the case that
        # a change occurs, this code will most likely either work correctly or crash in tests
        conn = connections["default"]
        if not conn.in_atomic_block:
            return []

        # atomic_blocks and savepoint_ids are merely used to identify the active
        # transaction/savepoint. They can be replaced with anything that does the same.
        savepoint_ids = [id(conn.atomic_blocks[0])]
        savepoint_ids.extend(sid for sid in conn.savepoint_ids if sid is not None)
        return savepoint_ids

    def _set_on_commit(self) -> None:
        if len(self.memos) == 1 and self.memos[0][0] != self.commiting:
            self.commiting = self.memos[0][0]
            transaction.on_commit(self._save_memo)

    def _update_memos(self) -> None:
        memo_ids = self._get_memo_ids()

        if len(self.memos) > len(memo_ids):
            del self.memos[len(memo_ids):]

        for i, memo_id in enumerate(memo_ids):
            if len(self.memos) <= i or memo_id != self.memos[i][0]:
                del self.memos[i:]
                self.memos.append((memo_id, {}))

    def _commit_memo(self) -> None:
        memo_ids = self._get_memo_ids()

        num_ids = len(memo_ids)
        if len(self.memos) <= num_ids:
            return

        self.memos[num_ids-1][1].update(self.memos[num_ids][1])
        del self.memos[num_ids:]

    def _discard_memo(self) -> None:
        memo_ids = self._get_memo_ids()
        del self.memos[len(memo_ids):]

    def _save_memo(self) -> None:
        if not self.memos:
            # Already saved
            return

        t = (time(), None)

        memo_ids = self._get_memo_ids()
        if memo_ids:
            # Still inside a transaction
            return

        memo = self.memos[0][1]
        # Update invalidation time to commit time
        memo = {
            k: t if v[1] is None else v
            for k,v in memo.items()
        }
        keys = list(memo.keys())
        items = _get_many(keys)
        for k in keys:
            if memo[k][0] < items.get(k, (0, None))[0]:
                # Data in cache is newer: can't trust either value as the
                # transaction may have modified the data. Invalidate the cache
                memo[k] = t

        _set_many(memo)

        self.memos.clear()
