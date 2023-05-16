from functools import partial
from uuid import uuid4

from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

from limiters import AsyncTokenBucket, SyncTokenBucket


def _tokenbucket_defaults():
    return {
        'name': uuid4().hex[:6],
        'capacity': 1,
        'refill_frequency': 1.0,
        'refill_amount': 1,
    }


def _async_defaults():
    return _tokenbucket_defaults() | {'connection': AsyncRedis.from_url('redis://127.0.0.1:6379')}


def _sync_defaults():
    return _tokenbucket_defaults() | {'connection': SyncRedis.from_url('redis://127.0.0.1:6379')}


def sync_tokenbucket_factory(**kwargs) -> partial:
    return partial(SyncTokenBucket, **{**_sync_defaults(), **kwargs})


def async_tokenbucket_factory(**kwargs) -> partial:
    return partial(AsyncTokenBucket, **{**_async_defaults(), **kwargs})
