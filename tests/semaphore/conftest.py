from functools import partial
from uuid import uuid4

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

from limiters import AsyncSemaphore, SyncSemaphore


def _semaphore_defaults():
    return {
        'name': uuid4().hex[:6],
        'capacity': 1,
    }


def _async_defaults():
    return _semaphore_defaults() | {'connection': AsyncRedis.from_url('redis://127.0.0.1:6379')}


def _sync_defaults():
    return _semaphore_defaults() | {'connection': SyncRedis.from_url('redis://127.0.0.1:6379')}


def sync_semaphore_factory(**kwargs) -> partial:
    return partial(SyncSemaphore, **{**_sync_defaults(), **kwargs})


def async_semaphore_factory(**kwargs) -> partial:
    return partial(AsyncSemaphore, **{**_async_defaults(), **kwargs})
